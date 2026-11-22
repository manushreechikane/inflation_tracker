import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from modules.data_management.database import create_db_engine, init_db, session_scope
from modules.data_management.models import Receipt, PurchaseItem


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
