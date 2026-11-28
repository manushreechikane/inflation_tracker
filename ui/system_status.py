"""Installation health check: OCR tooling, database and package versions."""
import sys
from importlib.metadata import PackageNotFoundError, version

import pandas as pd
import pytesseract
import streamlit as st
from sqlalchemy import func, select

from config import settings
from modules.data_management.database import session_scope
from modules.data_management.models import CPIData, Product, PurchaseItem, Receipt

PACKAGES = [
    "streamlit", "pandas", "numpy", "SQLAlchemy", "pytesseract", "opencv-python",
    "Pillow", "pdf2image", "plotly", "requests",
]


def _tesseract_status() -> tuple[bool, str]:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    try:
        return True, str(pytesseract.get_tesseract_version())
    except Exception:
        return False, "Not found — install Tesseract and set TESSERACT_CMD in .env"


def render_system_status() -> None:
    ok, detail = _tesseract_status()
    st.markdown(
        f"**Python** {sys.version.split()[0]} · "
        f"**Mode** {'public demo' if settings.PUBLIC_DEMO else 'private (SQLite)'} · "
        f"**Tesseract** {'ready' if ok else 'missing'}"
    )
    if ok:
        st.caption(f"Tesseract version: {detail}")
    else:
        st.warning(detail)

    with session_scope() as session:
        counts = {
            "receipts": session.scalar(select(func.count()).select_from(Receipt)),
            "purchase_items": session.scalar(select(func.count()).select_from(PurchaseItem)),
            "products": session.scalar(select(func.count()).select_from(Product)),
            "cpi_data": session.scalar(select(func.count()).select_from(CPIData)),
        }
    st.dataframe(
        pd.DataFrame({"table": list(counts), "rows": list(counts.values())}),
        hide_index=True, use_container_width=True,
    )
    st.caption(f"Database file: {settings.DATA_DIR / 'inflationlens.db'}")

    rows = []
    for package in PACKAGES:
        try:
            rows.append({"package": package, "version": version(package)})
        except PackageNotFoundError:
            rows.append({"package": package, "version": "not installed"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
