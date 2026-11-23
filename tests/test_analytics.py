from datetime import date

from sqlalchemy.orm import sessionmaker

from modules.analytics.analytics import personal_inflation, personal_price_history
from modules.data_management.database import create_db_engine, init_db, session_scope
from modules.data_management.models import Product, PurchaseItem, Receipt


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
    assert inflation.loc[inflation["product"] == "milk", "base_price"].iloc[0] == 50
    assert inflation.loc[inflation["product"] == "milk", "change_pct"].iloc[0] == 20
