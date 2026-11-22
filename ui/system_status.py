"""Phase 1 health check page: proves DB, config and OCR tooling are wired up."""
import sys
from importlib.metadata import PackageNotFoundError, version

import pandas as pd
import pytesseract
import streamlit as st
from sqlalchemy import func, select

from config import settings
from modules.data_management.database import session_scope
from modules.data_management.models import CPIData, Product, PurchaseItem, Receipt

PACKAGES = ["streamlit", "pandas", "numpy", "SQLAlchemy", "pytesseract",
            "opencv-python", "Pillow", "pdf2image", "plotly", "requests"]


def _tesseract_status() -> tuple[bool, str]:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    try:
        return True, str(pytesseract.get_tesseract_version())
    except Exception:
        return False, "Not found. Install Tesseract and set TESSERACT_CMD in .env"


def render_system_status() -> None:
    st.subheader("System status")

    ok, detail = _tesseract_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("Database", "Connected")
    c3.metric("Tesseract", "Ready" if ok else "Missing")
    if ok:
        st.caption(f"Tesseract version: {detail}")
    else:
        st.warning(detail)

    st.markdown("**Database tables**")
    with session_scope() as s:
        counts = {
            "receipts": s.scalar(select(func.count()).select_from(Receipt)),
            "purchase_items": s.scalar(select(func.count()).select_from(PurchaseItem)),
            "products": s.scalar(select(func.count()).select_from(Product)),
            "cpi_data": s.scalar(select(func.count()).select_from(CPIData)),
        }
    st.dataframe(pd.DataFrame({"table": list(counts.keys()), "rows": list(counts.values())}),
                 hide_index=True, use_container_width=True)
    st.caption(f"Database file: {settings.DATA_DIR / 'inflationlens.db'}")

    st.markdown("**Installed packages**")
    rows = []
    for pkg in PACKAGES:
        try:
            rows.append({"package": pkg, "version": version(pkg)})
        except PackageNotFoundError:
            rows.append({"package": pkg, "version": "NOT INSTALLED"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
