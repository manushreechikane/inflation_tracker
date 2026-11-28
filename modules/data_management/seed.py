"""Demo data: a realistic grocery basket that already has a story to tell.

The same fixtures feed both modes:
  * public demo mode loads them into ``st.session_state`` (nothing is written)
  * private mode can persist them with ``python -m modules.data_management.seed``

Prices are synthetic but shaped like real Indian grocery bills: staples creep
up, edible oil comes down, and one product shrinks its pack at the same price.
"""
from __future__ import annotations

import hashlib
from datetime import date
from random import Random

# name, category, brand, pack size (base unit), base unit, starting price,
# total drift over the whole window, extra qty bought per trip
CATALOGUE = [
    ("Amul Toned Milk 500 ml", "Dairy", "Amul", 500.0, "ml", 33.0, 0.085, 2),
    ("Aashirvaad Atta 5 kg", "Staples", "Aashirvaad", 5000.0, "g", 245.0, 0.215, 1),
    ("India Gate Basmati Rice 5 kg", "Staples", "India Gate", 5000.0, "g", 520.0, 0.140, 1),
    ("Tata Salt 1 kg", "Staples", "Tata", 1000.0, "g", 28.0, 0.040, 1),
    ("Toor Dal 1 kg", "Staples", "", 1000.0, "g", 145.0, 0.180, 1),
    ("Fortune Sunflower Oil 1 L", "Oils & Spices", "Fortune", 1000.0, "ml", 142.0, -0.055, 1),
    ("Britannia Brown Bread", "Bakery", "Britannia", 400.0, "g", 55.0, 0.090, 1),
    ("Farm Eggs 6 pcs", "Meat & Eggs", "", 6.0, "pcs", 48.0, 0.120, 1),
    ("Onion 1 kg", "Vegetables", "", 1000.0, "g", 42.0, 0.260, 1),
    ("Tomato 1 kg", "Vegetables", "", 1000.0, "g", 38.0, -0.090, 1),
    ("Surf Excel Easy Wash 1 kg", "Household", "Surf Excel", 1000.0, "g", 135.0, 0.060, 1),
    ("Amul Butter 500 g", "Dairy", "Amul", 500.0, "g", 285.0, 0.070, 1),
]

STORES = ["More Supermarket", "Local Kirana", "DMart"]

# The bread shrinks from 400 g to 375 g at this month index while the price
# keeps climbing: the classic shrinkflation case the app should call out.
SHRINK_MONTH = 6


def _month_starts(end: date, count: int) -> list[date]:
    months: list[date] = []
    year, month = end.year, end.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(months))


def _round_price(value: float) -> float:
    """Grocery prices land on friendly endings; keep them believable."""
    if value >= 100:
        return float(round(value))
    return round(value * 2) / 2 or 0.5


def demo_receipts(end: date | None = None, months: int = 9) -> list[dict]:
    """Build the seeded history, newest receipt last."""
    end = end or date.today()
    starts = _month_starts(end, months)
    rng = Random(20261128)
    receipts: list[dict] = []

    for month_index, month_start in enumerate(starts):
        progress = month_index / max(months - 1, 1)
        trips = [(4, STORES[month_index % len(STORES)]), (19, "Local Kirana")]
        for day, store in trips:
            try:
                purchase_date = date(month_start.year, month_start.month, day)
            except ValueError:  # pragma: no cover - defensive
                continue
            if purchase_date > end:
                continue

            items = []
            for name, category, brand, size, unit, base_price, drift, qty in CATALOGUE:
                # Milk and bread are bought on both trips, the big shop only
                # carries the rest on the first trip of the month.
                if day != 4 and name not in {"Amul Toned Milk 500 ml", "Britannia Brown Bread"}:
                    continue
                if day == 19 and name == "Britannia Brown Bread":
                    continue

                jitter = 1 + rng.uniform(-0.015, 0.015)
                price = _round_price(base_price * (1 + drift * progress) * jitter)

                pack_size = size
                if name == "Britannia Brown Bread" and month_index >= SHRINK_MONTH:
                    pack_size = 375.0

                items.append({
                    "product": name,
                    "category": category,
                    "brand": brand or None,
                    "package_size": pack_size,
                    "package_unit": unit,
                    "quantity": float(qty),
                    "unit_price": price,
                    "total_price": round(price * qty, 2),
                })

            if not items:
                continue
            receipts.append({
                "receipt_id": len(receipts) + 1,
                "store_name": store,
                "purchase_date": purchase_date,
                "receipt_total": round(sum(item["total_price"] for item in items), 2),
                "items": items,
                "seeded": True,
            })

    return receipts


def seed_database(session, end: date | None = None) -> int:
    """Persist the demo basket. No-op when any receipt already exists."""
    from sqlalchemy import func, select

    from modules.data_management.models import PurchaseItem, Receipt
    from modules.data_management.repository import get_or_create_product

    if (session.scalar(select(func.count()).select_from(Receipt)) or 0) > 0:
        return 0

    created = 0
    for record in demo_receipts(end):
        digest = hashlib.sha256(
            f"seed-{record['purchase_date']}-{record['store_name']}".encode()
        ).hexdigest()
        receipt = Receipt(
            store_name=record["store_name"],
            purchase_date=record["purchase_date"],
            receipt_total=record["receipt_total"],
            currency="INR",
            original_file_path="seed://demo",
            file_hash=digest,
            raw_ocr_text=None,
            processing_status="verified",
        )
        session.add(receipt)
        session.flush()

        for item in record["items"]:
            product = get_or_create_product(
                session,
                item["product"],
                brand=item["brand"],
                package_size=item["package_size"],
                package_unit=item["package_unit"],
                category=item["category"],
            )
            session.add(PurchaseItem(
                receipt_id=receipt.receipt_id,
                product_id=product.product_id,
                quantity=item["quantity"],
                package_size=item["package_size"],
                unit=item["package_unit"],
                total_price=item["total_price"],
                unit_price=item["unit_price"],
                verification_status="verified",
                ocr_product_name=item["product"],
                ocr_total_price=item["total_price"],
                user_corrected=False,
            ))
        created += 1
    return created


if __name__ == "__main__":  # pragma: no cover
    from modules.data_management.database import init_db, session_scope

    init_db()
    with session_scope() as session:
        count = seed_database(session)
    print(f"Seeded {count} receipts.")
