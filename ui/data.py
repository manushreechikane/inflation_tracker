"""One data access layer for both modes.

Public demo mode keeps receipts in a per-visitor workspace: each visitor gets a
short handle (carried in the ``?u=`` query string) and their own seeded copy of
the sample basket, so two people on the same deployment never see each other's
receipts. Private mode uses SQLite. Both hand back the same tidy history frame,
so every page is written once.
"""
from __future__ import annotations

import copy
import re
import secrets
import threading
from collections import OrderedDict
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from config import settings
from modules.analytics import analytics
from modules.data_management.database import session_scope
from modules.data_management.models import (
    CPIData,
    Product,
    PurchaseItem,
    Receipt,
)
from modules.data_management.repository import delete_receipt as _delete_receipt
from modules.data_management.repository import (
    find_receipt_by_hash,
    get_or_create_product,
    rename_product as _rename_product,
    set_product_category,
)
from modules.data_management.seed import demo_receipts
from modules.data_management.seed import seed_database as _seed_database
from modules.external_data.cpi import sample_cpi_frame


def is_demo() -> bool:
    return settings.PUBLIC_DEMO


def mode_label() -> str:
    return "Demo · sample basket" if is_demo() else "Local · SQLite"


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #

MAX_WORKSPACES = 128
_TOKEN = re.compile(r"^[0-9a-f]{6,12}$")

# One basket per visitor handle, newest used last so the oldest can be evicted.
# Demo receipts are a few hundred rows at most, so a bounded map is plenty.
_WORKSPACES: "OrderedDict[str, list[dict]]" = OrderedDict()
_WORKSPACE_LOCK = threading.RLock()


@st.cache_data(show_spinner=False)
def _seed_receipts() -> list[dict]:
    """The sample basket. Cached once, copied per workspace."""
    return demo_receipts()


def _new_workspace() -> list[dict]:
    return copy.deepcopy(_seed_receipts())


def visitor_id() -> str:
    """A short, random handle for this visitor's workspace.

    Kept in the address bar so a reload lands back in the same basket. It is an
    address, not a login: the data behind it is sample data.
    """
    known = st.session_state.get("visitor_id")
    if known:
        return str(known)

    token = ""
    try:
        raw = st.query_params.get("u")
        token = (raw[0] if isinstance(raw, list) else raw) or ""
        token = str(token).strip().lower()
    except Exception:  # no query params available: stay session-scoped
        token = ""

    if not _TOKEN.match(token):
        token = secrets.token_hex(4)
        try:
            st.query_params["u"] = token
        except Exception:
            pass

    st.session_state["visitor_id"] = token
    return token


def visitor_label() -> str:
    return f"Guest {visitor_id()[:4].upper()}"


def _workspace() -> list[dict]:
    key = visitor_id()
    with _WORKSPACE_LOCK:
        records = _WORKSPACES.get(key)
        if records is None:
            records = _new_workspace()
            _WORKSPACES[key] = records
            while len(_WORKSPACES) > MAX_WORKSPACES:
                _WORKSPACES.popitem(last=False)
        else:
            _WORKSPACES.move_to_end(key)
    return records


def receipts() -> list[dict]:
    if not is_demo():
        raise RuntimeError("SQLite mode reads through history() and receipt_table()")
    return _workspace()


def reset_demo() -> None:
    key = visitor_id()
    with _WORKSPACE_LOCK:
        _WORKSPACES[key] = _new_workspace()
        _WORKSPACES.move_to_end(key)


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
    """Persist a reviewed receipt. Returns the receipt id (string for the demo)."""
    if not items:
        raise ValueError("A receipt needs at least one item")

    if is_demo():
        with _WORKSPACE_LOCK:
            receipt_id = _next_demo_id()
            receipts().append({
                "receipt_id": receipt_id,
                "store_name": store_name or "Receipt",
                "purchase_date": purchase_date,
                "receipt_total": round(receipt_total, 2),
                "items": items,
                "seeded": False,
            })
        return str(receipt_id)

    from pathlib import Path  # local import keeps startup light

    from modules.receipt_processing.receipt_processor import save_upload, sha256_bytes

    with session_scope() as session:
        path: Path | None = None
        digest = sha256_bytes(raw_text.encode() if raw_text else f"{store_name}{purchase_date}".encode())
        if file_bytes:
            path, digest = save_upload(file_name or "receipt.png", file_bytes)
        if find_receipt_by_hash(session, digest):
            raise ValueError("This receipt has already been saved")

        receipt = Receipt(
            store_name=store_name or None,
            purchase_date=purchase_date,
            receipt_total=round(receipt_total, 2),
            currency=settings.DEFAULT_CURRENCY,
            original_file_path=str(path) if path else "manual://entry",
            file_hash=digest,
            raw_ocr_text=raw_text,
            processing_status="verified",
        )
        session.add(receipt)
        session.flush()

        for item in items:
            product = get_or_create_product(
                session,
                item["product"],
                brand=item.get("brand"),
                package_size=item.get("package_size"),
                package_unit=item.get("package_unit"),
                category=item.get("category"),
            )
            session.add(PurchaseItem(
                receipt_id=receipt.receipt_id,
                product_id=product.product_id,
                quantity=float(item.get("quantity") or 1),
                package_size=item.get("package_size"),
                unit=item.get("package_unit"),
                total_price=float(item["total_price"]),
                unit_price=float(item["unit_price"]),
                verification_status="verified",
                ocr_line_text=item.get("ocr_line_text"),
                ocr_product_name=item["product"],
                ocr_total_price=float(item["total_price"]),
                ocr_confidence=item.get("ocr_confidence"),
                user_corrected=bool(item.get("user_corrected", True)),
            ))
        return str(receipt.receipt_id)


def receipt_table() -> pd.DataFrame:
    columns = ["Receipt", "Date", "Store", "Items", "Total"]
    if is_demo():
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

    with session_scope() as session:
        rows = session.execute(
            select(
                Receipt.receipt_id,
                Receipt.purchase_date,
                Receipt.store_name,
                func.count(PurchaseItem.purchase_id),
                Receipt.receipt_total,
            )
            .outerjoin(PurchaseItem, PurchaseItem.receipt_id == Receipt.receipt_id)
            .group_by(Receipt.receipt_id)
            .order_by(Receipt.purchase_date.desc())
        ).all()
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame([
        {"Receipt": row[0], "Date": pd.Timestamp(row[1]), "Store": row[2] or "—",
         "Items": row[3], "Total": float(row[4] or 0)}
        for row in rows
    ], columns=columns)


def delete_receipt(receipt_id: int) -> bool:
    if is_demo():
        with _WORKSPACE_LOCK:
            records = receipts()
            before = len(records)
            records[:] = [
                receipt for receipt in records
                if int(receipt.get("receipt_id", -1)) != int(receipt_id)
            ]
            return len(records) < before
    with session_scope() as session:
        return _delete_receipt(session, int(receipt_id))


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #

def history(months: int | None = None) -> pd.DataFrame:
    if is_demo():
        return analytics.history_from_receipts(receipts(), months=months)
    with session_scope() as session:
        return analytics.personal_price_history(session, months=months)


def receipt_count() -> int:
    if is_demo():
        return len(receipts())
    with session_scope() as session:
        return int(session.scalar(select(func.count()).select_from(Receipt)) or 0)


def product_options() -> list[str]:
    history_frame = history()
    if history_frame.empty:
        return []
    return sorted(history_frame["product"].dropna().unique())


# --------------------------------------------------------------------------- #
# Product maintenance
# --------------------------------------------------------------------------- #

def set_category(product_name: str, category: str) -> None:
    if is_demo():
        for receipt in receipts():
            for item in receipt["items"]:
                if item.get("product") == product_name:
                    item["category"] = category
        return
    with session_scope() as session:
        product = session.scalar(select(Product).where(Product.product_name == product_name))
        if product:
            set_product_category(session, product, category)


def rename_product(product_name: str, new_name: str) -> None:
    new_name = new_name.strip()
    if not new_name or new_name == product_name:
        return
    if is_demo():
        existing = set(product_options())
        if new_name in existing:
            raise ValueError(f"'{new_name}' already exists")
        for receipt in receipts():
            for item in receipt["items"]:
                if item.get("product") == product_name:
                    item["product"] = new_name
        return
    with session_scope() as session:
        product = session.scalar(select(Product).where(Product.product_name == product_name))
        if product is None:
            raise ValueError("Product not found")
        _rename_product(session, product, new_name)


# --------------------------------------------------------------------------- #
# Official CPI
# --------------------------------------------------------------------------- #

def cpi_frame(country: str) -> tuple[pd.DataFrame, bool]:
    """Return (frame, is_sample). Falls back to the labelled sample series."""
    if is_demo():
        frame = sample_cpi_frame()
        frame = frame.rename(columns={"period": "period"})
        return frame, True

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


def seed_local_database() -> int:
    if is_demo():
        raise ValueError("Demo mode does not write to the database")
    with session_scope() as session:
        return _seed_database(session)


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
