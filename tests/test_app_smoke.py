"""Render every screen through Streamlit's own test harness.

This catches the failures that unit tests cannot: a renamed column, a chart
with an empty frame, a widget key collision, or markup that markdown decides
to print as a code block.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["overview", "scan", "basket", "cpi", "data"]
APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(scope="module")
def app() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=90)
    app.run()
    return app


def test_default_page_is_this_month(app):
    assert not app.exception
    assert app.session_state["page"] == "overview"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_demo_data(app, page):
    app.session_state["page"] = page
    app.run()
    assert not app.exception, f"{page} raised: {app.exception}"


@pytest.mark.parametrize("slug,months", [("3m", 3), ("6m", 6), ("12m", 12), ("all", 0)])
def test_window_buttons_change_the_window(app, slug, months):
    app.button(key=f"win_{slug}").click().run()
    assert app.session_state["months"] == months
    assert not app.exception


def test_no_markup_leaks_into_the_body(app):
    """Indented HTML used to render as a literal code block."""
    body = " ".join(block.value for block in app.markdown)
    assert 'class="il-kpi"' not in body
