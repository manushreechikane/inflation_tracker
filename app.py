import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE
from modules.data_management.database import init_db
from ui.system_status import render_system_status

st.set_page_config(page_title=APP_NAME, layout="wide")


@st.cache_resource
def _setup() -> bool:
    init_db()  # runs once per server process
    return True


_setup()

# (page name, phase in which it gets built). Only "System status" exists in Phase 1.
PAGES = {
    "System status": None,
    "Overview": 7,
    "Receipt scanner": 3,
    "My price history": 7,
    "Inflation analytics": 7,
    "Official CPI comparison": 7,
    "Settings & data": 7,
}

st.sidebar.title(APP_NAME)
st.sidebar.caption(APP_TAGLINE)
page = st.sidebar.radio("Navigate", list(PAGES))

st.title(page)
if PAGES[page] is None:
    render_system_status()
else:
    st.info(f"This page has not been built yet. It is scheduled for Phase {PAGES[page]}.")
