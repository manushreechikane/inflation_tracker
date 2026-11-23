import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE
from modules.data_management.database import init_db
from ui.system_status import render_system_status
from ui.pages import (
    render_cpi_comparison,
    render_inflation_analytics,
    render_overview,
    render_price_history,
    render_receipt_scanner,
    render_settings,
)

st.set_page_config(page_title=APP_NAME, layout="wide")


@st.cache_resource
def _setup() -> bool:
    init_db()  # runs once per server process
    return True


_setup()

PAGES = {
    "System status": None,
    "Overview": "overview",
    "Receipt scanner": "receipt",
    "My price history": "history",
    "Inflation analytics": "analytics",
    "Official CPI comparison": "cpi",
    "Settings & data": "settings",
}

st.sidebar.title(APP_NAME)
st.sidebar.caption(APP_TAGLINE)
page = st.sidebar.radio("Navigate", list(PAGES))

st.title(page)
PAGE_RENDERERS = {
    "overview": render_overview,
    "receipt": render_receipt_scanner,
    "history": render_price_history,
    "analytics": render_inflation_analytics,
    "cpi": render_cpi_comparison,
    "settings": render_settings,
}
if PAGES[page] is None:
    render_system_status()
else:
    PAGE_RENDERERS[PAGES[page]]()
