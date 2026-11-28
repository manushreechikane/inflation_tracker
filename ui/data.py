"""One data access layer, scoped to the signed-in account.

Every account keeps its own basket of receipts (seeded with a realistic sample
so the app is never empty), stored next to the account itself. Two people using
one deployment therefore never share a price history. The analytics package runs
on the same tidy frame either way, so every page is written once.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from config import settings
from modules.analytics import analytics
from modules.data_management.accounts import load_basket, save_basket
from modules.data_management.database import session_scope
from modules.data_management.models import CPIData, Product
from modules.data_management.seed import demo_receipts
from modules.external_data.cpi import sample_cpi_frame


def is_demo() -> bool:
    return settings.PUBLIC_DEMO


def mode_label() -> str:
    return "Demo · sample basket" if is_demo() else "Local · your data"


def _user_id() -> int | None:
    user = st.session_state.get("user") or {}
    try:
        return int(user.get("user_id"))
    except (TypeError, ValueError):
        return None


def _key(user_id: int) -> str:
    return f"basket_{user_id}"


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #

def receipts() -> list[dict]:
    """This account's receipts, loading (and seeding) from storage on first use."""
    user_id = _user_id()
    if user_id is None:
        return []

    key = _key(user_id)
    if key not in st.session_state:
        records = load_basket(user_id)
        if records is None:
            records = demo_receipts()
            save_basket(user_id, records)
        st.session_state[key] = records
    return st.session_state[key]


def _persist() -> None:
    user_id = _user_id()
    if user_id is not None:
        save_basket(user_id, receipts())


def seed_account_basket(user_id: int, force: bool = False) -> int:
    """Give a fresh account the sample basket (or leave an existing one alone)."""
    if force or load_basket(user_id) is None:
        records = demo_receipts()
        save_basket(user_id, records)
        st.session_state[_key(user_id)] = records
    return len(st.session_state.get(_key(user_id)) or [])


def reset_demo() -> None:
    user_id = _user_id()
    if user_id is None:
        return
    st.session_state[_key(user_id)] = demo_receipts()
    _persist()


def forget_basket(user_id: int) -> None:
    st.session_state.pop(_key(user_id), None)


def _next_demo_id() -> int:
    return max((int(receipt.get("receipt_id", 0)) for receipt in receipts()), default=0) + 1


def save_receipt(
    *,
    store_name: str,
    purchase_date: date,
    receipt_total: float,
    items: list[dict],
    raw_text: str | None = None,
    file_name: str | None = None,
    file_bytes: bytes | None = None,
) -> str:
    """Persist a reviewed receipt to this account's basket."""
    if not items:
        raise ValueError("A receipt needs at least one item")
    if _user_id() is None:
        raise ValueError("Sign in to save a receipt")

    receipt_id = _next_demo_id()
    receipts().append({
        "receipt_id": receipt_id,
        "store_name": store_name or "Receipt",
        "purchase_date": purchase_date,
        "receipt_total": round(float(receipt_total), 2),
        "items": items,
        "seeded": False,
    })
    _persist()
    return str(receipt_id)


def receipt_table() -> pd.DataFrame:
    columns = ["Receipt", "Date", "Store", "Items", "Total"]
    rows = [{
        "Receipt": int(receipt.get("receipt_id", index)),
        "Date": pd.Timestamp(receipt["purchase_date"]),
        "Store": receipt.get("store_name") or "—",
        "Items": len(receipt.get("items", [])),
        "Total": float(receipt.get("receipt_total") or 0),
    } for index, receipt in enumerate(receipts(), start=1)]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("Date", ascending=False)


def delete_receipt(receipt_id: int) -> bool:
    records = receipts()
    before = len(records)
    records[:] = [
        receipt for receipt in records
        if int(receipt.get("receipt_id", -1)) != int(receipt_id)
    ]
    changed = len(records) < before
    if changed:
        _persist()
    return changed


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #

def history(months: int | None = None) -> pd.DataFrame:
    return analytics.history_from_receipts(receipts(), months=months)


def receipt_count() -> int:
    return len(receipts())


def product_options() -> list[str]:
    history_frame = history()
    if history_frame.empty:
        return []
    return sorted(history_frame["product"].dropna().unique())


# --------------------------------------------------------------------------- #
# Product maintenance
# --------------------------------------------------------------------------- #

def set_category(product_name: str, category: str) -> None:
    for receipt in receipts():
        for item in receipt["items"]:
            if item.get("product") == product_name:
                item["category"] = category
    _persist()


def rename_product(product_name: str, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name or new_name == product_name:
        return
    if new_name in set(product_options()):
        raise ValueError(f"'{new_name}' already exists")
    for receipt in receipts():
        for item in receipt["items"]:
            if item.get("product") == product_name:
                item["product"] = new_name
    _persist()


# --------------------------------------------------------------------------- #
# Official CPI
# --------------------------------------------------------------------------- #

def cpi_frame(country: str) -> tuple[pd.DataFrame, bool]:
    """Return (frame, is_sample). Falls back to the labelled sample series."""
    if is_demo():
        return sample_cpi_frame(), True

    with session_scope() as session:
        frame = analytics.cpi_history(session, country)
    if frame.empty:
        return sample_cpi_frame(), True
    return frame, False


def cpi_has_real_data(country: str) -> bool:
    if is_demo():
        return False
    with session_scope() as session:
        return bool(session.scalar(
            select(func.count()).select_from(CPIData).where(CPIData.country == country)
        ))


def import_cpi_rows(country: str, rows: list[dict], source_type: str = "manual_import") -> int:
    from modules.external_data.cpi import store_rows

    if is_demo():
        raise ValueError("CPI imports are disabled in demo mode")
    with session_scope() as session:
        return store_rows(session, country, rows, source_type=source_type)


def export_frame() -> pd.DataFrame:
    frame = history()
    if frame.empty:
        return frame
    export = frame.copy()
    export["purchase_date"] = pd.to_datetime(export["purchase_date"]).dt.date
    return export.rename(columns={
        "purchase_date": "date",
        "product": "product",
        "category": "category",
        "quantity": "quantity",
        "unit_price": "unit_price",
        "total_price": "line_total",
        "store_name": "store",
    })


def product_catalogue() -> list[str]:
    """Every product name known to this account (used for rename pickers)."""
    with session_scope() as session:
        names = session.scalars(select(Product.product_name)).all()
    return sorted({*names, *product_options()})
