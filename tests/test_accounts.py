"""Accounts: sign-up, sign-in, profile edits, and one basket per person."""
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from modules.data_management import accounts
from modules.data_management.database import session_scope
from modules.data_management.models import AppUser


def _email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def test_sign_up_sign_in_and_profile_round_trip():
    email = _email()
    user = accounts.create_user(email, "grocery-2026", "Asha")

    assert user["email"] == email
    assert user["name"] == "Asha"
    assert user["monthly_budget"] is None

    signed_in = accounts.authenticate(email.upper(), "grocery-2026")
    assert signed_in is not None
    assert signed_in["user_id"] == user["user_id"]
    assert accounts.authenticate(email, "wrong-password") is None

    updated = accounts.update_profile(
        user["user_id"], monthly_budget=24000, household_size=4, goal="Cut 10%"
    )
    assert updated["monthly_budget"] == 24000
    assert updated["household_size"] == 4
    assert updated["goal"] == "Cut 10%"
    assert accounts.get_user(user["user_id"])["goal"] == "Cut 10%"


def test_password_change_replaces_the_old_one():
    email = _email()
    user = accounts.create_user(email, "grocery-2026", "Asha")

    accounts.change_password(user["user_id"], "grocery-2026", "new-password-9")
    assert accounts.authenticate(email, "grocery-2026") is None
    assert accounts.authenticate(email, "new-password-9") is not None

    with pytest.raises(ValueError):
        accounts.change_password(user["user_id"], "not-the-password", "another-one-1")


def test_duplicate_email_and_weak_password_are_rejected():
    email = _email()
    accounts.create_user(email, "grocery-2026", "One")

    with pytest.raises(ValueError):
        accounts.create_user(email.upper(), "grocery-2026", "Two")
    with pytest.raises(ValueError):
        accounts.create_user(_email(), "short", "Three")
    with pytest.raises(ValueError):
        accounts.create_user("not-an-email", "grocery-2026", "Four")


def test_passwords_are_stored_as_salted_hashes():
    email = _email()
    accounts.create_user(email, "secret-recipe-1", "Five")

    with session_scope() as session:
        row = session.scalar(select(AppUser).where(AppUser.email == email))
        assert row.password_hash != "secret-recipe-1"
        assert len(row.password_hash) == 64
        assert len(row.password_salt) == 32


def test_baskets_belong_to_one_account():
    first = accounts.create_user(_email(), "grocery-2026", "A")
    second = accounts.create_user(_email(), "grocery-2026", "B")

    accounts.save_basket(first["user_id"], [{
        "receipt_id": 1, "store_name": "Kirana",
        "purchase_date": date(2026, 11, 1), "receipt_total": 99.0,
        "items": [{"product": "Onion 1 kg", "quantity": 1.0,
                   "unit_price": 40.0, "total_price": 40.0}],
    }])

    loaded = accounts.load_basket(first["user_id"])
    assert loaded[0]["purchase_date"] == date(2026, 11, 1)
    assert loaded[0]["items"][0]["product"] == "Onion 1 kg"
    assert accounts.load_basket(second["user_id"]) is None


def test_deleting_an_account_removes_its_basket():
    user = accounts.create_user(_email(), "grocery-2026", "C")
    accounts.save_basket(user["user_id"], [{
        "receipt_id": 1, "purchase_date": date(2026, 11, 1), "items": [],
    }])

    accounts.delete_user(user["user_id"])

    assert accounts.get_user(user["user_id"]) is None
    assert accounts.load_basket(user["user_id"]) is None
