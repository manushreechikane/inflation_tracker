"""Profile: who you are, what you spend, and how the account is secured."""
from __future__ import annotations

import base64
import io

import streamlit as st
from PIL import Image, ImageOps

from config.constants import SUPPORTED_COUNTRIES, SUPPORTED_CURRENCIES
from modules.data_management import accounts
from ui import auth, data, theme


def _avatar_uri(upload) -> str:
    """Resize an uploaded picture to a small square and inline it as a data URI."""
    image = Image.open(io.BytesIO(upload.getvalue())).convert("RGB")
    image = ImageOps.fit(image, (256, 256), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _stats() -> list[tuple[str, str, str]]:
    history = data.history()
    receipts = data.receipt_count()
    products = int(history["product"].nunique()) if not history.empty else 0
    if history.empty:
        return [
            ("Receipts", str(receipts), "in your basket"),
            ("Products", str(products), "tracked"),
            ("Months", "0", "add a receipt to start"),
            ("Currency", theme.currency_symbol(), st.session_state["user"].get("currency", "")),
        ]
    months = int(history["purchase_date"].dt.to_period("M").nunique())
    spend = float(history["total_price"].sum())
    return [
        ("Receipts", str(receipts), "in your basket"),
        ("Products", str(products), "tracked"),
        ("Months", str(months), "of price history"),
        ("Spent so far", theme.compact_money(spend), "on the receipts you kept"),
    ]


def page_profile() -> None:
    user = auth.current_user()
    if user is None:
        st.stop()

    theme.section("Your profile", "who this basket belongs to")
    theme.kpis(_stats())

    left, right = st.columns([0.8, 1.2], gap="large")

    with left:
        with st.container(key="profile_card"):
            st.markdown(
                theme._blk(f"""
                <div class="il-avatar-wrap">{theme.avatar(user, 104)}</div>
                <div class="il-profile-name">{theme.esc(user['name'])}</div>
                <div class="il-profile-mail">{theme.esc(user['email'])}</div>
                """),
                unsafe_allow_html=True,
            )
            upload = st.file_uploader(
                "Profile picture", type=["png", "jpg", "jpeg"], key="avatar_upload",
                label_visibility="collapsed",
            )
            if upload is not None:
                try:
                    updated = accounts.update_profile(
                        int(user["user_id"]), avatar=_avatar_uri(upload)
                    )
                    auth.update_session_user(updated)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not use that picture: {exc}")
            if user.get("avatar"):
                if st.button("Remove picture", key="avatar_remove"):
                    auth.update_session_user(
                        accounts.update_profile(int(user["user_id"]), avatar=None)
                    )
                    st.rerun()
            theme.note("A square picture works best. It is resized before it is stored.")

    with right:
        with st.container(key="profile_form_card"):
            st.markdown(
                '<div class="il-form-title">Household &amp; budget</div>',
                unsafe_allow_html=True,
            )
            with st.form("profile_form", clear_on_submit=False):
                name = st.text_input("Display name", value=user["name"])
                budget_col, size_col = st.columns(2)
                budget = budget_col.number_input(
                    f"Budget ({theme.currency_symbol()})",
                    min_value=0.0, max_value=1_000_000.0,
                    value=float(user.get("monthly_budget") or 0.0), step=500.0,
                    format="%.0f",
                )
                household = size_col.number_input(
                    "Household size", min_value=1, max_value=20,
                    value=int(user.get("household_size") or 1), step=1, format="%d",
                )
                country_col, currency_col = st.columns(2)
                country = country_col.selectbox(
                    "Country", list(SUPPORTED_COUNTRIES),
                    index=list(SUPPORTED_COUNTRIES).index(user.get("country") or "IN"),
                    format_func=lambda code: SUPPORTED_COUNTRIES[code]["label"],
                )
                currency = currency_col.selectbox(
                    "Currency", list(SUPPORTED_CURRENCIES),
                    index=list(SUPPORTED_CURRENCIES).index(user.get("currency") or "INR"),
                    format_func=lambda code: f"{SUPPORTED_CURRENCIES[code]} {code}",
                )
                goal = st.text_input(
                    "What are you trying to do?",
                    value=user.get("goal") or "",
                    placeholder="Keep the weekly bill under ₹1,500",
                )
                saved = st.form_submit_button("Save profile", type="primary")

            if saved:
                try:
                    updated = accounts.update_profile(
                        int(user["user_id"]),
                        name=name, monthly_budget=float(budget),
                        household_size=int(household), country=country,
                        currency=currency, goal=goal,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    auth.update_session_user(updated)
                    st.session_state["country"] = country
                    st.success("Profile saved.")
                    st.rerun()

            theme.note(
                "Your budget is what the coach plans against, and your currency sets every "
                "amount in the app."
            )

        with st.expander("Email & password"):
            st.markdown(f"**Signed in as** {theme.esc(user['email'])}")
            with st.form("password_form", clear_on_submit=True):
                current = st.text_input("Current password", type="password")
                new = st.text_input("New password", type="password")
                confirm = st.text_input("Confirm new password", type="password")
                changed = st.form_submit_button("Change password")
            if changed:
                if new != confirm:
                    st.error("The two new passwords do not match.")
                else:
                    try:
                        accounts.change_password(int(user["user_id"]), current, new)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Password changed.")

        with st.expander("Your data"):
            frame = data.export_frame()
            st.markdown(
                f"**{data.receipt_count()} receipts** and "
                f"**{len(frame)} line items** are stored against this account."
            )
            if not frame.empty:
                st.download_button(
                    "Download your basket (CSV)",
                    frame.to_csv(index=False).encode("utf-8"),
                    file_name="inflationlens-basket.csv",
                    mime="text/csv",
                )
            theme.note(
                "Receipts are stored with the account, not on this device: signing in on "
                "another browser shows the same basket."
            )

        with st.expander("Close my account"):
            theme.note(
                "This deletes the account, the basket and the profile picture. It cannot be "
                "undone."
            )
            confirm_delete = st.checkbox(
                "I understand this deletes my account", key="confirm_delete"
            )
            if st.button("Delete account", key="delete_account",
                         disabled=not confirm_delete):
                accounts.delete_user(int(user["user_id"]))
                auth.sign_out()
                st.rerun()

        if st.button("Sign out", key="profile_signout"):
            auth.sign_out()
            st.rerun()
