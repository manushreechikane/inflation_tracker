"""Accounts, profiles and per-account baskets.

A small, self-contained account store sitting in the same SQLite file as the
rest of the project. Passwords are hashed with PBKDF2-HMAC-SHA256 and a per-user
salt; the plain password never reaches the database or the logs.

This is deliberately not a full identity provider — there is no email
verification or password reset. It exists so several people can use one
deployment without sharing a basket.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from modules.data_management.database import init_db, session_scope
from modules.data_management.models import AppUser, UserBasket

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
MIN_PASSWORD = 8
_ITERATIONS = 210_000

PROFILE_FIELDS = {
    "name", "avatar", "country", "currency", "monthly_budget", "household_size", "goal",
}


def normalize_email(email: str | None) -> str:
    return str(email or "").strip().lower()


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()


def _salt() -> str:
    return secrets.token_hex(16)


def as_dict(user: AppUser) -> dict[str, Any]:
    """The public shape of an account: no hash, no salt."""
    return {
        "user_id": int(user.user_id),
        "email": user.email,
        "name": user.name,
        "avatar": user.avatar,
        "country": user.country,
        "currency": user.currency,
        "monthly_budget": user.monthly_budget,
        "household_size": user.household_size,
        "goal": user.goal,
    }


def validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD:
        raise ValueError(f"Use at least {MIN_PASSWORD} characters for the password.")


def create_user(email: str, password: str, name: str = "") -> dict[str, Any]:
    email = normalize_email(email)
    if not EMAIL.match(email):
        raise ValueError("That email address does not look right.")
    validate_password(password)

    init_db()
    with session_scope() as session:
        existing = session.scalar(select(AppUser).where(AppUser.email == email))
        if existing is not None:
            raise ValueError("An account with that email already exists — try signing in.")
        salt = _salt()
        user = AppUser(
            email=email,
            name=(str(name or "").strip() or email.split("@")[0])[:80],
            password_hash=_hash(password, salt),
            password_salt=salt,
        )
        session.add(user)
        session.flush()
        return as_dict(user)


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    email = normalize_email(email)
    if not email or not password:
        return None
    init_db()
    with session_scope() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == email))
        if user is None:
            return None
        if not hmac.compare_digest(user.password_hash, _hash(password, user.password_salt)):
            return None
        return as_dict(user)


def get_user(user_id: int) -> dict[str, Any] | None:
    init_db()
    with session_scope() as session:
        user = session.get(AppUser, int(user_id))
        return as_dict(user) if user is not None else None


def update_profile(user_id: int, **fields) -> dict[str, Any]:
    """Save any subset of the editable profile fields."""
    unknown = set(fields) - PROFILE_FIELDS
    if unknown:
        raise ValueError(f"Unknown profile fields: {', '.join(sorted(unknown))}")

    if "name" in fields:
        name = str(fields["name"] or "").strip()
        if not name:
            raise ValueError("A display name cannot be empty.")
        fields["name"] = name[:80]
    if "monthly_budget" in fields and fields["monthly_budget"] is not None:
        budget = float(fields["monthly_budget"])
        if budget < 0:
            raise ValueError("A budget cannot be negative.")
        fields["monthly_budget"] = round(budget, 2)
    if "household_size" in fields and fields["household_size"] is not None:
        size = int(fields["household_size"])
        if not 1 <= size <= 20:
            raise ValueError("Household size should be between 1 and 20.")
        fields["household_size"] = size
    if "country" in fields:
        fields["country"] = str(fields["country"]).upper()[:2]
    if "currency" in fields:
        fields["currency"] = str(fields["currency"]).upper()[:3]
    if "goal" in fields and fields["goal"] is not None:
        fields["goal"] = str(fields["goal"]).strip()[:200] or None

    init_db()
    with session_scope() as session:
        user = session.get(AppUser, int(user_id))
        if user is None:
            raise ValueError("That account no longer exists.")
        for key, value in fields.items():
            setattr(user, key, value)
        session.flush()
        return as_dict(user)


def change_password(user_id: int, current: str, new: str) -> None:
    validate_password(new)
    init_db()
    with session_scope() as session:
        user = session.get(AppUser, int(user_id))
        if user is None:
            raise ValueError("That account no longer exists.")
        if not hmac.compare_digest(user.password_hash, _hash(current, user.password_salt)):
            raise ValueError("The current password is not right.")
        salt = _salt()
        user.password_salt = salt
        user.password_hash = _hash(new, salt)


def delete_user(user_id: int) -> None:
    """Delete the account; the basket goes with it through the FK cascade."""
    init_db()
    with session_scope() as session:
        user = session.get(AppUser, int(user_id))
        if user is not None:
            session.delete(user)
            session.flush()


# --------------------------------------------------------------------------- #
# One basket per account
# --------------------------------------------------------------------------- #

def _encode(records: list[dict]) -> str:
    rows = []
    for record in records:
        row = dict(record)
        purchased = row.get("purchase_date")
        if isinstance(purchased, (date, datetime)):
            row["purchase_date"] = purchased.isoformat()
        rows.append(row)
    return json.dumps(rows)


def _decode(payload: str) -> list[dict]:
    rows = json.loads(payload or "[]")
    for row in rows:
        purchased = row.get("purchase_date")
        if isinstance(purchased, str):
            try:
                row["purchase_date"] = date.fromisoformat(purchased[:10])
            except ValueError:
                row["purchase_date"] = None
    return rows


def load_basket(user_id: int) -> list[dict] | None:
    """The account's receipts, or None when the account has never saved any."""
    init_db()
    with session_scope() as session:
        basket = session.get(UserBasket, int(user_id))
        return _decode(basket.payload) if basket is not None else None


def save_basket(user_id: int, records: list[dict]) -> None:
    init_db()
    payload = _encode(records)
    with session_scope() as session:
        basket = session.get(UserBasket, int(user_id))
        if basket is None:
            session.add(UserBasket(user_id=int(user_id), payload=payload))
        else:
            basket.payload = payload
