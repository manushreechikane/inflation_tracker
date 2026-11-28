"""The coach must quote the basket it was given, not invented numbers."""
import pandas as pd

from ui.coach import answer, build_plan


def _ctx() -> dict:
    inflation = pd.DataFrame([
        {"product": "Onion 1 kg", "category": "Vegetables", "base_month": "2026-03",
         "latest_month": "2026-11", "base_price": 41.5, "latest_price": 53.0,
         "change_pct": 27.7, "observations": 9, "spend": 900.0, "weight_pct": 12.0},
        {"product": "Aashirvaad Atta 5 kg", "category": "Staples", "base_month": "2026-03",
         "latest_month": "2026-11", "base_price": 245.0, "latest_price": 292.5,
         "change_pct": 19.4, "observations": 9, "spend": 2200.0, "weight_pct": 28.0},
    ])
    spend = pd.DataFrame([
        {"month": "2026-10", "spend": 5400.0},
        {"month": "2026-11", "spend": 6050.0},
    ])
    shrink = pd.DataFrame([{
        "product": "Britannia Brown Bread", "base_size": 400.0, "latest_size": 375.0,
        "unit_label": "100 g", "price_change_pct": 9.9, "per_unit_change_pct": 17.2,
        "flagged": True,
    }])
    spread = pd.DataFrame([{
        "product": "Amul Butter 500 g", "store_name": "DMart", "latest_price": 285.0,
        "vs_cheapest_pct": 6.0,
    }])
    return {
        "name": "Asha", "currency": "INR", "budget": 18000.0,
        "goal": "Keep the weekly bill under control", "household": 2,
        "receipts": 18, "months": 12, "empty": False,
        "inflation": inflation, "spend": spend, "shrink": shrink, "spread": spread,
        "change": 11.3, "official": 3.4, "is_sample": True, "products": 12,
        "last_month_spend": 6050.0, "avg_monthly_spend": 5725.0, "months_tracked": 9,
    }


def test_plan_quotes_the_budget_and_the_movers():
    plan = build_plan(_ctx())

    assert "Asha" in plan
    assert "18,000" in plan
    assert "11,950" in plan  # 18,000 - 6,050 of headroom
    assert "Onion 1 kg" in plan
    assert "Britannia Brown Bread" in plan
    assert "DMart" in plan


def test_plan_refuses_to_invent_numbers_for_an_empty_basket():
    plan = build_plan({"empty": True, "name": "Asha"})
    assert "nothing in the basket" in plan.lower()


def test_answers_quote_the_right_figures():
    ctx = _ctx()

    budget = answer("Am I inside my budget?", ctx)
    assert "6,050" in budget and "18,000" in budget and "under" in budget

    movers = answer("What got more expensive?", ctx)
    assert "Onion 1 kg" in movers and "+27.7%" in movers

    cpi = answer("How do I compare with CPI?", ctx)
    assert "11.3" in cpi and "3.4" in cpi and "sample" in cpi

    fallback = answer("tell me a joke", ctx)
    assert "Build my plan" in fallback
