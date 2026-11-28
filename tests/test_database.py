from datetime import date

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from modules.data_management.database import create_db_engine, init_db, session_scope
from modules.data_management.models import Product, ProductAlias, PurchaseItem, Receipt
from modules.data_management.repository import (
    delete_receipt,
    find_alias,
    get_or_create_product,
    normalize_name,
    rename_product,
)


@pytest.fixture
def test_session_factory(tmp_path):
    eng = create_db_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    init_db(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _receipt(file_hash="a" * 64):
    return Receipt(original_file_path="x.png", file_hash=file_hash)


def test_all_tables_created(test_session_factory):
    eng, _ = test_session_factory
    expected = {"receipts", "products", "product_aliases", "purchase_items", "cpi_data"}
    assert expected <= set(inspect(eng).get_table_names())


def test_duplicate_file_hash_rejected(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        s.add(_receipt())
    with pytest.raises(IntegrityError):
        with session_scope(factory) as s:
            s.add(_receipt())


def test_foreign_key_enforced(test_session_factory):
    _, factory = test_session_factory
    with pytest.raises(IntegrityError):
        with session_scope(factory) as s:
            s.add(PurchaseItem(receipt_id=999, total_price=10.0))  # receipt 999 doesn't exist


def test_transaction_rolls_back_on_error(test_session_factory):
    _, factory = test_session_factory
    with pytest.raises(RuntimeError):
        with session_scope(factory) as s:
            s.add(_receipt("b" * 64))
            s.flush()
            raise RuntimeError("boom")
    with session_scope(factory) as s:
        assert s.query(Receipt).count() == 0


def test_product_identity_keeps_pack_sizes_apart(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        small = get_or_create_product(s, "Milk", package_size=500, package_unit="ml")
        large = get_or_create_product(s, "Milk", package_size=1000, package_unit="ml")
        assert small.product_id != large.product_id
        assert large.package_size == 1000


def test_same_product_twice_does_not_duplicate_or_crash(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        first = get_or_create_product(s, "Amul Toned Milk 500 ml", package_size=500,
                                      package_unit="ml", category="Dairy")
        second = get_or_create_product(s, "Amul Toned Milk 500 ml", package_size=500,
                                       package_unit="ml")
        assert first.product_id == second.product_id
    with session_scope(factory) as s:
        assert s.query(Product).count() == 1
        assert s.query(ProductAlias).count() == 1


def test_alias_redirects_a_new_spelling(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        product = get_or_create_product(s, "AMUL MLK 500ML", package_size=500, package_unit="ml")
        alias = find_alias(s, "amul mlk 500ml")
        assert alias is not None and alias.product_id == product.product_id


def test_rename_keeps_the_old_spelling_as_an_alias(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        product = get_or_create_product(s, "MLK TONED 500", package_size=500, package_unit="ml")
        rename_product(s, product, "Amul Toned Milk 500 ml")
        product_id = product.product_id
    with session_scope(factory) as s:
        alias = find_alias(s, "MLK TONED 500")
        assert alias is not None and alias.product_id == product_id
        resolved = get_or_create_product(s, "MLK TONED 500", package_size=500, package_unit="ml")
        assert resolved.product_id == product_id


def test_normalize_name_strips_punctuation():
    assert normalize_name("  Amul  Toned-Milk!! ") == "amul toned milk"


def test_delete_receipt_cascades_to_items(test_session_factory):
    _, factory = test_session_factory
    with session_scope(factory) as s:
        receipt = Receipt(original_file_path="x.png", file_hash="c" * 64,
                          purchase_date=date(2026, 1, 1))
        product = Product(product_name="Milk", normalized_name="milk")
        s.add_all([receipt, product])
        s.flush()
        s.add(PurchaseItem(receipt_id=receipt.receipt_id, product_id=product.product_id,
                           total_price=50, unit_price=50))
        receipt_id = receipt.receipt_id

    with session_scope(factory) as s:
        assert delete_receipt(s, receipt_id) is True
    with session_scope(factory) as s:
        assert s.scalar(select(PurchaseItem).where(PurchaseItem.receipt_id == receipt_id)) is None
