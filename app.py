"""InflationLens — entry point.

Navigation and the reporting window live in the sidebar, the way a paper
ledger has its index down the side; the body is one continuous story.
"""
import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE
from modules.data_management.database import init_db
from ui import data, theme
from ui.pages import PAGE_LABELS, PAGES, render_flash

st.set_page_config(
    page_title=f"{APP_NAME} — {APP_TAGLINE}",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="auto",
)


@st.cache_resource
def _setup() -> bool:
    init_db()  # runs once per server process
    return True


WINDOWS = [("3m", "3 mo", 3), ("6m", "6 mo", 6), ("12m", "12 mo", 12), ("all", "All", 0)]


def _sidebar() -> None:
    st.session_state.setdefault("page", "overview")
    st.session_state.setdefault("months", 12)

    with st.sidebar:
        theme.brand(data.mode_label(), data.visitor_label())

        theme.side_label("Ledger")
        with st.container(key="navlist"):
            for slug, label in PAGE_LABELS.items():
                active = st.session_state["page"] == slug
                if st.button(label, key=f"nav_{slug}", use_container_width=True,
                             type="primary" if active else "secondary"):
                    st.session_state["page"] = slug
                    st.rerun()

        theme.side_label("Window")
        with st.container(key="windowgrid"):
            rows = [WINDOWS[:2], WINDOWS[2:]]
            for row in rows:
                cols = st.columns(2, gap="small")
                for col, (slug, label, months) in zip(cols, row):
                    active = int(st.session_state["months"]) == months
                    if col.button(label, key=f"win_{slug}", use_container_width=True,
                                  type="primary" if active else "secondary"):
                        st.session_state["months"] = months
                        st.rerun()

        theme.side_foot(
            f"<b>{theme.esc(data.visitor_label())}</b> — your own workspace.<br>"
            "Receipts you add are never visible to another visitor."
        )


MOBILE_LABELS = {
    "overview": "This month",
    "scan": "Add a receipt",
    "basket": "Basket",
    "cpi": "vs. CPI",
    "data": "Data",
}


def _mobile_nav() -> None:
    """A second copy of the controls, shown only under 780px.

    Streamlit collapses the sidebar on narrow screens without drawing a toggle,
    so a phone would otherwise have no way to change screen or window.
    """
    with st.container(key="mobilenav"):
        with st.container(key="mnav_pages"):
            for slug, label in MOBILE_LABELS.items():
                active = st.session_state["page"] == slug
                if st.button(label, key=f"mnav_{slug}",
                             type="primary" if active else "secondary"):
                    st.session_state["page"] = slug
                    st.rerun()
        with st.container(key="mnav_windows"):
            for slug, label, months in WINDOWS:
                active = int(st.session_state["months"]) == months
                if st.button(label, key=f"mwin_{slug}",
                             type="primary" if active else "secondary"):
                    st.session_state["months"] = months
                    st.rerun()


_setup()
theme.apply()
_sidebar()
_mobile_nav()

render_flash()
PAGES[st.session_state["page"]]()
theme.footer()
