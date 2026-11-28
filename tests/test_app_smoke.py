"""Render every screen through Streamlit's own test harness.

This catches the failures that unit tests cannot: a renamed column, a chart
with an empty frame, a widget key collision.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["This month", "Add a receipt", "My basket", "vs. CPI", "Data"]
APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(scope="module")
def app() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=90)
    app.run()
    return app


def test_default_page_is_this_month(app):
    assert not app.exception
    assert app.radio(key="nav").value == "This month"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_demo_data(app, page):
    app.radio(key="nav").set_value(page).run()
    assert not app.exception, f"{page} raised: {app.exception}"
