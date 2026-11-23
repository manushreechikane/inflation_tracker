"""Streamlit page implementations."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select

from config import settings
from config.constants import SUPPORTED_CURRENCIES
from modules.analytics.analytics import cpi_history, personal_inflation, personal_price_history
from modules.data_management.database import session_scope
from modules.data_management.models import PurchaseItem, Receipt
from modules.data_management.repository import get_or_create_product, upsert_cpi
from modules.receipt_processing.receipt_processor import (
    extract_text,
    extract_text_from_upload,
    parse_receipt,
    save_upload,
)


def _session_history() -> pd.DataFrame:
    rows = []
    for receipt in st.session_state.get("demo_receipts", []):
        for item in receipt["items"]:
            rows.append({
                "purchase_date": receipt["purchase_date"],
                "product": item["product"],
                "unit_price": item["price"],
                "store_name": receipt["store_name"],
            })
    return pd.DataFrame(rows, columns=[
        "purchase_date", "product", "unit_price", "store_name"
    ])


def _session_inflation(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["product", "base_price", "latest_price", "change_pct"])

    history = history.copy()
    history["purchase_date"] = pd.to_datetime(history["purchase_date"])
    history["month"] = history["purchase_date"].dt.to_period("M").astype(str)
    monthly = history.groupby(["product", "month"], as_index=False)["unit_price"].median()
    results = []
    for product, frame in monthly.groupby("product"):
        frame = frame.sort_values("month")
        base = float(frame.iloc[0]["unit_price"])
        latest = float(frame.iloc[-1]["unit_price"])
        results.append({
            "product": product,
            "base_price": base,
            "latest_price": latest,
            "change_pct": round(((latest / base) - 1) * 100, 2) if base else 0,
        })
    return pd.DataFrame(results).sort_values("change_pct", ascending=False)


def render_overview() -> None:
    st.subheader("Overview")
    if settings.PUBLIC_DEMO:
        history = _session_history()
        receipt_count = len(st.session_state.get("demo_receipts", []))
        inflation = _session_inflation(history)
        st.caption("Demo data is private to this browser session and is not saved.")
    else:
        with session_scope() as s:
            receipt_count = s.scalar(select(func.count()).select_from(Receipt)) or 0
            inflation = personal_inflation(s)
    c1, c2 = st.columns(2)
    c1.metric("Receipts", receipt_count)
    c2.metric("Tracked products", len(inflation))
    if not inflation.empty:
        st.plotly_chart(
            px.bar(inflation, x="product", y="change_pct", title="Personal price change by product"),
            use_container_width=True,
        )
    else:
        st.info("Upload a receipt and verify its items to begin tracking.")


def render_receipt_scanner() -> None:
    st.subheader("Receipt scanner")
    if settings.PUBLIC_DEMO:
        _render_demo_receipt_scanner()
        return

    uploaded = st.file_uploader("Upload receipt", type=["jpg", "jpeg", "png", "pdf"])
    if not uploaded:
        return

    data = uploaded.getvalue()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"File exceeds {settings.MAX_UPLOAD_MB} MB.")
        return

    try:
        path, file_hash = save_upload(uploaded.name, data)
    except ValueError as exc:
        st.error(str(exc))
        return

    with session_scope() as s:
        if s.scalar(select(Receipt).where(Receipt.file_hash == file_hash)):
            st.warning("This receipt has already been uploaded.")
            return

    try:
        raw_text = extract_text(path)
    except Exception as exc:
        raw_text = ""
        st.warning(str(exc))

    parsed = parse_receipt(raw_text)
    st.caption("OCR text is retained for audit purposes. You can correct the parsed values below.")
    store_name = st.text_input("Store", parsed["store_name"] or "")
    purchase_date = st.date_input("Purchase date", parsed["purchase_date"])
    receipt_total = st.number_input("Receipt total", min_value=0.0, value=float(parsed["receipt_total"] or 0), step=1.0)

    rows = parsed["items"]
    if rows:
        edited = st.data_editor(
            pd.DataFrame(rows),
            column_config={
                "ocr_product_name": "Product",
                "ocr_total_price": st.column_config.NumberColumn("Price", min_value=0.0),
            },
            hide_index=True,
            num_rows="dynamic",
            key="receipt_items",
        )
    else:
        edited = pd.DataFrame(
            [{"ocr_product_name": "", "ocr_total_price": 0.0, "ocr_line_text": ""}]
        )
        edited = st.data_editor(edited, num_rows="dynamic", key="manual_receipt_items")

    if st.button("Save receipt", type="primary"):
        try:
            with session_scope() as s:
                receipt = Receipt(
                    store_name=store_name or None,
                    purchase_date=purchase_date,
                    receipt_total=receipt_total,
                    currency=settings.DEFAULT_CURRENCY,
                    original_file_path=str(path),
                    file_hash=file_hash,
                    raw_ocr_text=raw_text,
                    processing_status="ocr_success" if raw_text else "ocr_failed",
                )
                s.add(receipt)
                s.flush()
                for row in edited.to_dict("records"):
                    name = str(row.get("ocr_product_name") or "").strip()
                    price = float(row.get("ocr_total_price") or 0)
                    if not name or price <= 0:
                        continue
                    product = get_or_create_product(s, name)
                    s.add(PurchaseItem(
                        receipt_id=receipt.receipt_id,
                        product_id=product.product_id,
                        quantity=1,
                        total_price=price,
                        unit_price=price,
                        ocr_line_text=row.get("ocr_line_text"),
                        ocr_product_name=name,
                        ocr_total_price=price,
                        verification_status="verified",
                    ))
            st.success("Receipt saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save receipt: {exc}")


def _render_demo_receipt_scanner() -> None:
    st.info("Public demo mode: receipts are processed in memory and saved only to this browser session.")
    uploaded = st.file_uploader("Upload receipt", type=["jpg", "jpeg", "png", "pdf"])
    if not uploaded:
        return

    data = uploaded.getvalue()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"File exceeds {settings.MAX_UPLOAD_MB} MB.")
        return
    try:
        raw_text = extract_text_from_upload(uploaded.name, data)
    except Exception as exc:
        st.error(f"Could not read receipt: {exc}")
        return

    parsed = parse_receipt(raw_text)
    store_name = st.text_input("Store", parsed["store_name"] or "", key="demo_store")
    purchase_date = st.date_input("Purchase date", parsed["purchase_date"], key="demo_date")
    st.text_area("OCR text", raw_text, height=120, key="demo_ocr_text")
    items = parsed["items"] or [
        {"ocr_product_name": "", "ocr_total_price": 0.0, "ocr_line_text": ""}
    ]
    edited = st.data_editor(
        pd.DataFrame(items),
        column_config={
            "ocr_product_name": "Product",
            "ocr_total_price": st.column_config.NumberColumn("Price", min_value=0.0),
        },
        hide_index=True,
        num_rows="dynamic",
        key="demo_receipt_items",
    )
    if st.button("Add to this session", type="primary"):
        saved_items = []
        for row in edited.to_dict("records"):
            name = str(row.get("ocr_product_name") or "").strip()
            price = float(row.get("ocr_total_price") or 0)
            if name and price > 0:
                saved_items.append({"product": name, "price": price})
        if not saved_items:
            st.error("Enter at least one product and a price.")
            return
        st.session_state.setdefault("demo_receipts", []).append({
            "store_name": store_name or "Receipt",
            "purchase_date": purchase_date,
            "items": saved_items,
        })
        st.success("Added to this browser session only.")
        st.rerun()


def render_price_history() -> None:
    st.subheader("My price history")
    if settings.PUBLIC_DEMO:
        history = _session_history()
    else:
        with session_scope() as s:
            history = personal_price_history(s)
    if history.empty:
        st.info("No verified item prices yet.")
        return
    history["purchase_date"] = pd.to_datetime(history["purchase_date"])
    product = st.selectbox("Product", sorted(history["product"].unique()))
    subset = history[history["product"] == product].sort_values("purchase_date")
    st.plotly_chart(px.line(subset, x="purchase_date", y="unit_price", markers=True), use_container_width=True)
    st.dataframe(subset, hide_index=True, use_container_width=True)


def render_inflation_analytics() -> None:
    st.subheader("Inflation analytics")
    if settings.PUBLIC_DEMO:
        result = _session_inflation(_session_history())
    else:
        with session_scope() as s:
            result = personal_inflation(s)
    if result.empty:
        st.info("No analytics available until verified receipt items exist.")
        return
    st.dataframe(result, hide_index=True, use_container_width=True)
    st.plotly_chart(
        px.bar(result, x="product", y="change_pct", title="Change from earliest to latest purchase"),
        use_container_width=True,
    )


def render_cpi_comparison() -> None:
    st.subheader("Official CPI comparison")
    country = st.selectbox("Country", ["IN", "US"], format_func=lambda x: {"IN": "India", "US": "United States"}[x])
    if settings.PUBLIC_DEMO:
        personal = _session_inflation(_session_history())
        official = pd.DataFrame(columns=["period", "category", "index_value"])
        st.info("Official CPI imports are disabled in public demo mode to prevent shared data changes.")
    else:
        with session_scope() as s:
            personal = personal_inflation(s)
            official = cpi_history(s, country)
    if not official.empty:
        st.plotly_chart(
            px.line(official, x="period", y="index_value", color="category", title="Official CPI"),
            use_container_width=True,
        )
    if not personal.empty:
        st.markdown("**Personal product change**")
        st.dataframe(personal, hide_index=True, use_container_width=True)
    if personal.empty and official.empty:
        st.info("No personal or official CPI data has been added yet.")


def render_settings() -> None:
    st.subheader("Settings & data")
    if settings.PUBLIC_DEMO:
        st.info("Public demo mode is enabled. Data imports are disabled; nothing is written to the shared database.")
        return

    country = st.selectbox("Default country", ["IN", "US"], format_func=lambda x: {"IN": "India", "US": "United States"}[x])
    currency = st.selectbox("Default currency", list(SUPPORTED_CURRENCIES), format_func=lambda x: f"{SUPPORTED_CURRENCIES[x]} {x}")

    st.markdown("**Import CPI data**")
    uploaded = st.file_uploader("CPI CSV", type=["csv"])
    if uploaded:
        frame = pd.read_csv(uploaded)
        st.dataframe(frame.head(), hide_index=True)
        required = {"period", "index_value"}
        if required.issubset(frame.columns):
            if st.button("Import CPI rows"):
                count = 0
                with session_scope() as s:
                    for row in frame.to_dict("records"):
                        period = pd.to_datetime(row["period"], errors="coerce")
                        value = float(row["index_value"])
                        if pd.isna(period) or value < 0:
                            continue
                        upsert_cpi(
                            s,
                            country=country,
                            source=str(row.get("source", "Manual import")),
                            source_type="manual_import",
                            series_id=str(row.get("series_id", "MANUAL")),
                            category=str(row.get("category", "All items")),
                            period=period.date(),
                            index_value=value,
                        )
                        count += 1
                st.success(f"Imported {count} CPI rows.")
        else:
            st.error("CSV must contain period and index_value columns.")

    st.caption(f"Database: {settings.DATA_DIR / 'inflationlens.db'}")
