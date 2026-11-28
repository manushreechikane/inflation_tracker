"""Render every screen through Streamlit's own test harness.

This catches the failures that unit tests cannot: a renamed column, a chart
with an empty frame, a widget key collision, or markup that markdown decides
to print as a code block.
"""
import uuid
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from modules.data_management import accounts

PAGES = ["overview", "scan", "basket", "cpi", "coach", "profile", "data"]
APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(scope="module")
def app() -> AppTest:
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    user = accounts.create_user(email, "smoke-test-2026", "Smoke Tester")
    accounts.update_profile(user["user_id"], monthly_budget=18000.0)

    app = AppTest.from_file(str(APP), default_timeout=120)
    app.session_state["user"] = accounts.get_user(user["user_id"])
    app.run()
    return app


def test_signed_out_visitor_gets_the_login_screen():
    app = AppTest.from_file(str(APP), default_timeout=120)
    app.run()
    assert not app.exception
    assert "user" not in app.session_state
    body = " ".join(block.value for block in app.markdown)
    assert "Inflation" in body
    assert not any(button.key and str(button.key).startswith("nav_") for button in app.button)


def test_default_page_is_this_month(app):
    assert not app.exception
    assert app.session_state["page"] == "overview"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_a_signed_in_account(app, page):
    app.session_state["page"] = page
    app.run()
    assert not app.exception, f"{page} raised: {app.exception}"


@pytest.mark.parametrize("slug,months", [("3m", 3), ("6m", 6), ("12m", 12), ("all", 0)])
def test_window_buttons_change_the_window(app, slug, months):
    app.button(key=f"win_{slug}").click().run()
    assert app.session_state["months"] == months
    assert not app.exception


def test_hidden_mobile_pills_control_screen_and_window(app):
    """The mobile copy is invisible on desktop, so it must not fight the sidebar."""
    app.session_state["page"] = "overview"
    app.run()

    app.pills(key="mnav_pages").set_value("Plan").run()
    assert app.session_state["page"] == "coach"

    app.pills(key="mnav_windows").set_value("3 mo").run()
    assert app.session_state["months"] == 3
    assert not app.exception


def test_markup_is_emitted_on_single_lines(app):
    """Indented HTML used to render as a literal code block; one line cannot."""
    app.session_state["page"] = "overview"
    app.run()
    blocks = [block.value for block in app.markdown if 'class="il-kpi"' in block.value]
    assert blocks, "the KPI strip did not render at all"
    for block in blocks:
        assert "\n" not in block.strip(), "multi-line HTML would render as code"
