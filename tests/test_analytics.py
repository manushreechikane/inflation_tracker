from datetime import date

import pandas as pd
from sqlalchemy.orm import sessionmaker

from modules.analytics.analytics import (
    basket_change,
    basket_index,
    category_breakdown,
    cpi_rebased,
    history_from_receipts,
    personal_inflation,
    personal_price_history,
    shrinkflation,
    spend_by_month,
    store_spread,
)
from modules.data_management.database import create_db_engine, init_db, session_scope
from modules.data_management.models import Product, PurchaseItem, Receipt
from modules.data_management.seed import demo_receipts


def _history(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=[
        "receipt_id", "purchase_date", "product", "product_id", "category", "brand",
        "package_size", "package_unit", "quantity", "unit_price", "total_price",
        "store_name",
    ])


def _row(day, product, price, quantity=1, size=None, unit=None, store="Shop", category="Staples"):
    return {
        "receipt_id": 1,
        "purchase_date": pd.Timestamp(day),
        "product": product,
        "product_id": None,
        "category": category,
        "brand": None,
        "package_size": size,
        "package_unit": unit,
        "quantity": quantity,
        "unit_price": price,
        "total_price": price * quantity,
        "store_name": store,
    }


def test_personal_inflation_calculates_monthly_change(tmp_path):
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'analytics.db').as_posix()}")
    init_db(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_scope(factory) as session:
        receipt_one = Receipt(
            store_name="Fresh Mart",
            purchase_date=date(2026, 1, 15),
            receipt_total=100,
            original_file_path="one.png",
            file_hash="a" * 64,
        )
        receipt_two = Receipt(
            store_name="Fresh Mart",
            purchase_date=date(2026, 3, 15),
            receipt_total=120,
            original_file_path="two.png",
            file_hash="b" * 64,
        )
        milk = Product(product_name="Milk", normalized_name="milk")
        session.add_all([receipt_one, receipt_two, milk])
        session.flush()
        session.add_all([
            PurchaseItem(
                receipt_id=receipt_one.receipt_id,
                product_id=milk.product_id,
                unit_price=50,
                total_price=50,
                verification_status="verified",
            ),
            PurchaseItem(
                receipt_id=receipt_two.receipt_id,
                product_id=milk.product_id,
                unit_price=60,
                total_price=60,
                verification_status="verified",
            ),
        ])

    with session_scope(factory) as session:
        history = personal_price_history(session)
        inflation = personal_inflation(session)

    assert len(history) == 2
    assert inflation.loc[inflation["product"] == "Milk", "base_price"].iloc[0] == 50
    assert inflation.loc[inflation["product"] == "Milk", "change_pct"].iloc[0] == 20


def test_products_with_one_observation_are_excluded():
    history = _history([
        _row("2026-01-05", "Milk", 50),
        _row("2026-02-05", "Milk", 55),
        _row("2026-02-06", "Salt", 28),
    ])
    inflation = personal_inflation(history)
    assert list(inflation["product"]) == ["Milk"]


def test_basket_index_rebases_to_100_and_tracks_the_basket():
    history = _history([
        _row("2026-01-05", "Milk", 50),
        _row("2026-01-05", "Atta", 100),
        _row("2026-02-05", "Milk", 55),
        _row("2026-02-05", "Atta", 110),
        _row("2026-03-05", "Milk", 60),
        _row("2026-03-05", "Atta", 130),
    ])
    index = basket_index(history)
    assert list(index["index"]) == [100.0, 110.0, 126.67]
    assert basket_change(personal_inflation(history)) == 26.67


def test_shrinkflation_flags_a_smaller_pack_at_a_higher_price():
    history = _history([
        _row("2026-01-05", "Brown Bread", 55, size=400, unit="g", category="Bakery"),
        _row("2026-03-05", "Brown Bread", 60, size=375, unit="g", category="Bakery"),
    ])
    flags = shrinkflation(history)
    row = flags.iloc[0]
    assert row["size_change_pct"] == -6.2
    assert bool(row["flagged"]) is True
    assert row["per_unit_change_pct"] > 16


def test_store_spread_compares_the_same_product():
    history = _history([
        _row("2026-01-05", "Milk", 50, store="Kirana"),
        _row("2026-01-06", "Milk", 58, store="Supermarket"),
    ])
    spread = store_spread(history)
    assert len(spread) == 2
    assert spread["vs_cheapest_pct"].max() == 16.0


def test_category_breakdown_weights_by_spend():
    history = _history([
        _row("2026-01-05", "Milk", 50, category="Dairy"),
        _row("2026-02-05", "Milk", 60, category="Dairy"),
        _row("2026-01-05", "Salt", 20, category="Staples"),
        _row("2026-02-05", "Salt", 20, category="Staples"),
    ])
    breakdown = category_breakdown(personal_inflation(history))
    dairy = breakdown[breakdown["category"] == "Dairy"].iloc[0]
    assert dairy["change_pct"] == 20
    assert dairy["weight_pct"] > 60


def test_spend_by_month_sums_line_totals():
    history = _history([
        _row("2026-01-05", "Milk", 50, quantity=2),
        _row("2026-02-05", "Milk", 55),
    ])
    monthly = spend_by_month(history)
    assert list(monthly["spend"]) == [100.0, 55.0]


def test_cpi_rebased_sets_the_base_month_to_100():
    cpi = pd.DataFrame({
        "period": ["2026-01", "2026-02", "2026-03"],
        "category": ["All items"] * 3,
        "series_id": ["X"] * 3,
        "index_value": [100.0, 105.0, 110.0],
    })
    rebased = cpi_rebased(cpi, "2026-02")
    assert list(rebased["index"]) == [100.0, 104.76]


def test_demo_history_runs_through_the_same_pipeline():
    receipts = demo_receipts(date(2026, 11, 28))
    assert len(receipts) >= 10

    history = history_from_receipts(receipts)
    assert not history.empty
    assert history["product"].nunique() >= 8

    index = basket_index(history)
    assert len(index) >= 6
    assert index["index"].iloc[0] == 100.0
    assert index["index"].iloc[-1] > 100

    inflation = personal_inflation(history)
    assert not inflation.empty
    assert basket_change(inflation) > 5

    flags = shrinkflation(history)
    assert bool(flags["flagged"].any())


def test_history_respects_the_month_window():
    receipts = demo_receipts(date(2026, 11, 28))
    full = history_from_receipts(receipts)
    recent = history_from_receipts(receipts, months=3, today=date(2026, 11, 28))
    assert recent["purchase_date"].min() > full["purchase_date"].min()
