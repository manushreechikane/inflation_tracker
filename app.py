"""InflationLens — entry point.

Sign in first; then navigation and the reporting window live in the sidebar, the
way a paper ledger has its index down the side, and the body is one continuous
story.
"""
import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE
from modules.data_management.database import init_db
from ui import auth, data, theme
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


def _sidebar(user: dict) -> None:
    st.session_state.setdefault("page", "overview")
    st.session_state.setdefault("months", 12)

    with st.sidebar:
        theme.account(user, data.mode_label())

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

        theme.side_foot("Your basket is private to this account.")
        if st.button("Sign out", key="signout", use_container_width=True):
            auth.sign_out()
            st.rerun()


MOBILE_LABELS = {
    "overview": "This month",
    "scan": "Receipt",
    "basket": "Basket",
    "cpi": "CPI",
    "coach": "Plan",
    "profile": "You",
    "data": "Data",
}


def _sync_page_pill() -> None:
    label = st.session_state.get("mnav_pages")
    for slug, text in MOBILE_LABELS.items():
        if text == label:
            st.session_state["page"] = slug
            return


def _sync_window_pill() -> None:
    label = st.session_state.get("mnav_windows")
    for _slug, text, months in WINDOWS:
        if text == label:
            st.session_state["months"] = months
            return


def _mobile_nav() -> None:
    """A second copy of the controls, shown only under 780px.

    Streamlit collapses the sidebar on narrow screens without drawing a toggle,
    so a phone would otherwise have no way to change screen or window. The pills
    only write state when they are actually tapped, so the hidden copy can never
    fight the sidebar on a wide screen.
    """
    with st.container(key="mobilenav"):
        st.pills(
            "Screen", list(MOBILE_LABELS.values()),
            default=MOBILE_LABELS[st.session_state["page"]],
            key="mnav_pages", label_visibility="collapsed",
            on_change=_sync_page_pill,
        )
        window_labels = [label for _slug, label, _months in WINDOWS]
        current_window = next(
            (label for _slug, label, months in WINDOWS
             if months == int(st.session_state["months"])), window_labels[2]
        )
        st.pills(
            "Window", window_labels, default=current_window, key="mnav_windows",
            label_visibility="collapsed", on_change=_sync_window_pill,
        )


_setup()
theme.apply()

user = auth.current_user()
if user is None:
    auth.render_auth()
    st.stop()

_sidebar(user)
_mobile_nav()

render_flash()
PAGES.get(st.session_state.get("page", "overview"), PAGES["overview"])()
theme.footer()
