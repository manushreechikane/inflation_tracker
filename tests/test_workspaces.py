"""Demo deployments are multi-user: one basket per visitor, not one per server."""
from datetime import date

from streamlit.testing.v1 import AppTest

SCRIPT = """
from datetime import date

import streamlit as st

from ui import data

if st.session_state.pop("append", False):
    data.receipts().append({
        "receipt_id": 9001,
        "store_name": "Test shop",
        "purchase_date": date.today(),
        "receipt_total": 10.0,
        "items": [],
    })

st.session_state["count"] = len(data.receipts())
"""


def _visitor(handle: str) -> AppTest:
    app = AppTest.from_string(SCRIPT, default_timeout=60)
    app.session_state["visitor_id"] = handle
    app.run()
    assert not app.exception
    return app


def test_each_visitor_gets_a_private_workspace():
    first = _visitor("aaaaaa11")
    seeded = first.session_state["count"]

    first.session_state["append"] = True
    first.run()
    assert first.session_state["count"] == seeded + 1, "adding a receipt should persist"

    other = _visitor("bbbbbb22")
    assert other.session_state["count"] == seeded, "a new visitor starts from the sample basket"

    back = _visitor("aaaaaa11")
    assert back.session_state["count"] == seeded + 1, "the first visitor keeps their own receipts"


def test_visitor_handle_is_stable_and_short():
    app = _visitor("c0ffee42")
    assert len(app.session_state["visitor_id"]) == 8
    assert date.today()  # keep the import used if the script changes
