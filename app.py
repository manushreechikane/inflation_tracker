"""InflationLens — entry point.

A single narrative page rather than a dashboard: this month, add a receipt,
your basket, against official CPI, data. Navigation is text tabs, the sidebar is
gone, and the framework chrome is hidden in :mod:`ui.theme`.
"""
import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE
from modules.data_management.database import init_db
from ui import data, theme
from ui.pages import PAGES, render_flash

st.set_page_config(
    page_title=f"{APP_NAME} — {APP_TAGLINE}",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def _setup() -> bool:
    init_db()  # runs once per server process
    return True


_setup()
theme.apply()

theme.masthead(data.mode_label())

page = st.radio(
    "Navigate",
    list(PAGES),
    horizontal=True,
    label_visibility="collapsed",
    key="nav",
)

render_flash()
PAGES[page]()
theme.footer()
