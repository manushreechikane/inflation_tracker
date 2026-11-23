"""Personal and official inflation calculations."""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.data_management.models import CPIData, Product, PurchaseItem, Receipt


def personal_price_history(session: Session) -> pd.DataFrame:
    rows = session.execute(
        select(
            Receipt.purchase_date,
            Product.normalized_name,
            PurchaseItem.unit_price,
            PurchaseItem.total_price,
            PurchaseItem.quantity,
            Receipt.store_name,
        )
        .join(PurchaseItem, PurchaseItem.receipt_id == Receipt.receipt_id)
        .join(Product, PurchaseItem.product_id == Product.product_id)
        .where(PurchaseItem.verification_status == "verified")
        .order_by(Receipt.purchase_date)
    ).all()
    if not rows:
        return pd.DataFrame(columns=[
            "purchase_date", "product", "unit_price", "store_name"
        ])
    return pd.DataFrame(rows, columns=[
        "purchase_date", "product", "unit_price", "store_name"
    ])


def personal_inflation(session: Session) -> pd.DataFrame:
    history = personal_price_history(session)
    if history.empty:
        return pd.DataFrame(columns=["product", "base_price", "latest_price", "change_pct"])

    history["purchase_date"] = pd.to_datetime(history["purchase_date"])
    history["month"] = history["purchase_date"].dt.to_period("M").astype(str)
    monthly = history.groupby(["product", "month"], as_index=False)["unit_price"].median()
    output = []
    for product, frame in monthly.groupby("product"):
        frame = frame.sort_values("month")
        base = float(frame.iloc[0]["unit_price"])
        latest = float(frame.iloc[-1]["unit_price"])
        output.append({
            "product": product,
            "base_price": base,
            "latest_price": latest,
            "change_pct": ((latest / base) - 1) * 100 if base else 0,
        })
    return pd.DataFrame(output).sort_values("change_pct", ascending=False)


def cpi_history(session: Session, country: str = "IN") -> pd.DataFrame:
    rows = session.execute(
        select(CPIData.period, CPIData.category, CPIData.index_value)
        .where(CPIData.country == country)
        .order_by(CPIData.period)
    ).all()
    if not rows:
        return pd.DataFrame(columns=["period", "category", "index_value"])
    return pd.DataFrame(rows, columns=["period", "category", "index_value"])
