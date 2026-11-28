"""Sign in, create an account, and session handling.

The sign-in screen is the first thing a visitor sees, so it is built from the
same printed-grocery vocabulary as the rest of the app rather than Streamlit
defaults.
"""
from __future__ import annotations

import secrets

import streamlit as st

from config import settings
from modules.data_management import accounts
from ui import data, theme


def current_user() -> dict | None:
    user = st.session_state.get("user")
    return user if isinstance(user, dict) and user.get("user_id") else None


def sign_in(user: dict) -> None:
    """Put an authenticated account in the session and load its settings."""
    st.session_state["user"] = user
    st.session_state["page"] = "overview"
    st.session_state["months"] = settings.DEFAULT_WINDOW_MONTHS
    st.session_state["country"] = user.get("country") or settings.DEFAULT_COUNTRY
    st.session_state.pop("chat", None)
    data.seed_account_basket(int(user["user_id"]))


def sign_out() -> None:
    user = current_user()
    if user:
        data.forget_basket(int(user["user_id"]))
    for key in ("user", "chat", "page", "months", "country"):
        st.session_state.pop(key, None)


def update_session_user(user: dict) -> None:
    st.session_state["user"] = user
    st.session_state["country"] = user.get("country") or settings.DEFAULT_COUNTRY


def _guest_account() -> dict:
    """A throwaway account so a reviewer can look around without signing up."""
    handle = secrets.token_hex(3)
    user = accounts.create_user(
        f"guest-{handle}@inflationlens.demo",
        secrets.token_urlsafe(18),
        f"Guest {handle.upper()}",
    )
    return accounts.update_profile(
        user["user_id"],
        monthly_budget=18000.0,
        household_size=2,
        goal="Keep the weekly grocery bill under control",
        currency="INR",
        country="IN",
    )


def _aside() -> None:
    with st.container(key="authaside"):
        st.markdown(
            theme._blk(f"""
            <div class="il-auth-aside">
              <div class="il-wordmark">Inflation<em>Lens</em></div>
              <div class="il-auth-line">Your groceries. Your prices.
                Your real inflation.</div>
              <div class="il-auth-points">
                <div><b>One basket per account.</b> Receipts you add are yours;
                  another visitor never sees them.</div>
                <div><b>Your own index.</b> Prices weighted by what you actually
                  spend, next to official CPI.</div>
                <div><b>A plan, not a dashboard.</b> A budget, a coach, and the
                  three lines that moved.</div>
              </div>
              {theme._sticker()}
            </div>
            """),
            unsafe_allow_html=True,
        )


def _sign_in_form() -> None:
    with st.form("signin", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        user = accounts.authenticate(email, password)
        if user is None:
            st.error("That email and password do not match an account.")
            return
        sign_in(user)
        st.rerun()


def _sign_up_form() -> None:
    with st.form("signup", clear_on_submit=False):
        name = st.text_input("Name", placeholder="What should we call you?", key="signup_name")
        email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        password = st.text_input(
            "Password", type="password", key="signup_password",
            help=f"At least {accounts.MIN_PASSWORD} characters.",
        )
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
        budget = st.number_input(
            "Monthly grocery budget", min_value=0.0, value=18000.0, step=500.0,
            help="Used by the plan builder. You can change it any time.",
        )
        submitted = st.form_submit_button("Create my account", type="primary")

    if submitted:
        if password != confirm:
            st.error("The two passwords do not match.")
            return
        try:
            user = accounts.create_user(email, password, name)
            user = accounts.update_profile(user["user_id"], monthly_budget=float(budget))
        except ValueError as exc:
            st.error(str(exc))
            return
        sign_in(user)
        st.rerun()


def render_auth() -> None:
    """The signed-out screen: sign in, create an account, or look around."""
    left, middle, right = st.columns([1, 0.95, 0.15], gap="large")
    with left:
        _aside()
    with middle:
        with st.container(key="authcard"):
            theme.side_label("Welcome")
            choice = st.radio(
                "Mode", ["Sign in", "Create account"], horizontal=True,
                label_visibility="collapsed", key="auth_mode",
            )
            if choice == "Sign in":
                _sign_in_form()
            else:
                _sign_up_form()

            st.markdown('<div class="il-rule"></div>', unsafe_allow_html=True)
            if st.button("Look around with a sample account", key="auth_guest",
                         use_container_width=True):
                sign_in(_guest_account())
                st.rerun()
            theme.note(
                "Sample accounts get their own copy of the demo basket and can be "
                "abandoned without signing up."
            )
    with right:
        st.empty()
