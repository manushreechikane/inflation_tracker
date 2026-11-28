"""A coach that turns the basket into a plan you can actually follow.

No API key, no network: every answer is computed from this account's receipts
and budget, so the numbers in the plan are the same numbers on the charts.
"""
from __future__ import annotations

import streamlit as st

import pandas as pd

from config.constants import SUPPORTED_COUNTRIES
from modules.analytics.analytics import (
    basket_change,
    cpi_rebased,
    cpi_series_options,
    personal_inflation,
    shrinkflation,
    spend_by_month,
    store_spread,
)
from ui import auth, data, theme


# --------------------------------------------------------------------------- #
# Context and reasoning
# --------------------------------------------------------------------------- #

def build_context(months: int | None = None) -> dict:
    history = data.history(months)
    user = auth.current_user() or {}
    ctx: dict = {
        "name": (user.get("name") or "there").split()[0],
        "currency": user.get("currency") or "INR",
        "budget": user.get("monthly_budget"),
        "goal": user.get("goal"),
        "household": user.get("household_size") or 1,
        "receipts": data.receipt_count(),
        "months": months or 12,
        "empty": history.empty,
    }
    if history.empty:
        return ctx

    inflation = personal_inflation(history)
    monthly = spend_by_month(history)

    # This calendar month is still being shopped, so compare against the last
    # month that is actually finished — otherwise a single early receipt looks
    # like a sudden drop in spending.
    today_month = str(pd.Timestamp.today().to_period("M"))
    complete = monthly[monthly["month"] < today_month] if len(monthly) > 1 else monthly
    reference = complete.iloc[-1] if not complete.empty else monthly.iloc[-1]
    flags = shrinkflation(history)
    spread = store_spread(history)
    cpi, is_sample = data.cpi_frame(
        st.session_state.get("country") or user.get("country") or "IN"
    )
    first_month = None
    if not history.empty:
        first_month = history["purchase_date"].dt.to_period("M").astype(str).min()
    series = cpi_series_options(cpi)
    series_id = next((sid for sid, label in series if "all items" in label.lower()),
                     series[0][0] if series else None)
    official = cpi_rebased(cpi, first_month, series_id) if first_month else None

    ctx.update({
        "history": history,
        "inflation": inflation,
        "spend": monthly,
        "shrink": flags[flags["flagged"]] if not flags.empty else flags,
        "spread": spread,
        "change": basket_change(inflation),
        "official": (
            round(float(official.iloc[-1]["index"]) - 100, 1)
            if official is not None and not official.empty else None
        ),
        "is_sample": is_sample,
        "products": int(history["product"].nunique()),
        "last_month": str(reference["month"]) if not monthly.empty else "",
        "last_month_spend": float(reference["spend"]) if not monthly.empty else 0.0,
        "avg_monthly_spend": float(monthly["spend"].mean()) if not monthly.empty else 0.0,
        "months_tracked": int(history["purchase_date"].dt.to_period("M").nunique()),
    })
    return ctx


def _money(ctx: dict, value) -> str:
    return theme.money(value, decimals=0, currency=ctx.get("currency"))


def _weekly_cap(budget: float) -> float:
    return round(budget / 4.33 / 50) * 50


def _unit_of(label: str) -> str:
    """'100 g' -> 'g', so a pack change reads '400 g → 375 g'."""
    parts = str(label).split()
    return parts[-1] if parts else "g"


def build_plan(ctx: dict) -> str:
    """A short, specific plan, computed from the basket and the budget."""
    budget = ctx.get("budget")
    if ctx.get("empty"):
        return (
            "There is nothing in the basket yet, so any plan would be invented. "
            "Add one receipt — even a small one — and I can work with your real prices."
        )

    lines: list[str] = []
    name = ctx["name"]
    last = ctx.get("last_month_spend") or 0.0
    avg = ctx.get("avg_monthly_spend") or 0.0

    when = theme.month_label(ctx.get("last_month") or "") if ctx.get("last_month") else ""
    when = when or "Your last full month"
    if budget:
        cap = _weekly_cap(float(budget))
        if last > budget:
            lines.append(
                f"**1. Close the gap.** {when} came to {_money(ctx, last)} against a "
                f"budget of {_money(ctx, budget)} — {_money(ctx, last - budget)} over. "
                f"A weekly cap of {_money(ctx, cap)} gets you back inside."
            )
        else:
            lines.append(
                f"**1. Keep the rhythm.** {when} came to {_money(ctx, last)} against a "
                f"budget of {_money(ctx, budget)}, so you have {_money(ctx, budget - last)} "
                f"of room. A weekly cap of {_money(ctx, cap)} keeps it that way."
            )
    else:
        suggested = round(avg * 1.05 / 100) * 100 if avg else 0
        lines.append(
            f"**1. Set a number.** You are spending about {_money(ctx, avg)} a month. "
            f"Setting a budget near {_money(ctx, suggested)} in your profile gives the plan "
            "something to measure against."
        )

    inflation = ctx.get("inflation")
    if inflation is not None and not inflation.empty:
        top = inflation.head(3)
        detail = " · ".join(
            f"{row['product']} {row['change_pct']:+.1f}%" for _, row in top.iterrows()
        )
        lines.append(
            f"**2. Watch three lines.** {detail}. These are the products moving fastest "
            "in your own basket, not the national average."
        )
        worst = top.iloc[0]
        monthly_cost = (float(worst["spend"]) / max(ctx.get("months_tracked") or 1, 1))
        if monthly_cost:
            lines.append(
                f"**3. Put a number on it.** {worst['product']} costs you about "
                f"{_money(ctx, monthly_cost)} a month at your usual quantities. One cheaper "
                "pack or one skipped purchase there is worth more than trimming five small ones."
            )

    shrink = ctx.get("shrink")
    if shrink is not None and not shrink.empty:
        row = shrink.iloc[0]
        unit = _unit_of(row["unit_label"])
        lines.append(
            f"**4. Check the pack, not just the price.** {row['product']} went "
            f"{row['base_size']:g} {unit} → {row['latest_size']:g} {unit} while the "
            f"shelf price moved {row['price_change_pct']:+.0f}% — per {row['unit_label']} it "
            f"is {row['per_unit_change_pct']:+.0f}%."
        )

    spread = ctx.get("spread")
    if spread is not None and not spread.empty:
        row = spread.sort_values("vs_cheapest_pct", ascending=False).iloc[0]
        if float(row["vs_cheapest_pct"]) > 1:
            lines.append(
                f"**5. Same item, different shelf.** {row['product']} was "
                f"{row['vs_cheapest_pct']:+.0f}% dearer at {row['store_name']} than the "
                "cheapest store in your receipts."
            )

    goal = ctx.get("goal")
    closing = (
        f"That is the plan against your goal — *{goal}*."
        if goal else "Two receipts a month is enough to keep this plan honest."
    )
    return f"**{name}, here is the plan.**\n\n" + "\n\n".join(lines) + f"\n\n{closing}"


def answer(prompt: str, ctx: dict) -> str:
    """One deterministic reply per question, always grounded in the basket."""
    text = (prompt or "").lower()
    if ctx.get("empty"):
        return (
            "I cannot compute anything yet — the basket is empty. Add a receipt on "
            "**Add a receipt**, or load the sample, and ask me again."
        )

    if any(word in text for word in ("plan", "start", "what should i do", "help me")):
        return build_plan(ctx)

    if any(word in text for word in ("budget", "afford", "cap", "overspend", "save money")):
        budget = ctx.get("budget")
        last = ctx.get("last_month_spend") or 0.0
        if not budget:
            return (
                f"You have not set a budget yet. Your last month came to {_money(ctx, last)}; "
                "set a monthly number in **You → Household & budget** and I will plan against it."
            )
        gap = float(budget) - last
        verdict = (
            f"you finished {_money(ctx, gap)} under it"
            if gap >= 0 else f"you finished {_money(ctx, -gap)} over it"
        )
        when = theme.month_label(ctx.get("last_month") or "") if ctx.get("last_month") else "Last month"
        month_name = {
            "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
            "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
            "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December",
        }
        label = month_name.get(when.split()[0], when) if when else "Last month"
        return (
            f"{label}: **{_money(ctx, last)}** against a budget of "
            f"**{_money(ctx, budget)}** — {verdict}. That is about "
            f"{_money(ctx, last / 4.33)} a week; the cap I would aim for is "
            f"{_money(ctx, _weekly_cap(float(budget)))}."
        )

    if any(word in text for word in ("expensive", "increase", "riser", "rising", "went up",
                                     "inflation", "moved")):
        inflation = ctx.get("inflation")
        if inflation is None or inflation.empty:
            return "No product has two recorded prices yet, so there is no change to report."
        top = inflation.head(4)
        rows = "\n".join(
            f"- **{row['product']}** {row['change_pct']:+.1f}% "
            f"({theme.money(row['base_price'], currency=ctx['currency'])} → "
            f"{theme.money(row['latest_price'], currency=ctx['currency'])})"
            for _, row in top.iterrows()
        )
        change = ctx.get("change")
        headline = f"Your basket is {change:+.1f}% on the first month." if change is not None else ""
        return f"{headline}\n\n{rows}"

    if any(word in text for word in ("cpi", "official", "compare", "national")):
        change, official = ctx.get("change"), ctx.get("official")
        if change is None:
            return "A single month of receipts is a starting point, not a trend."
        if official is None:
            return f"Your basket is **{change:+.1f}%**. No official series is loaded to compare against."
        sample = " The CPI series in this build is a sample one." if ctx.get("is_sample") else ""
        relation = "above" if change > official else "below"
        return (
            f"Your basket: **{change:+.1f}%**. Official CPI over the same months: "
            f"**{official:+.1f}%**, so you are {abs(change - official):.1f} points {relation}. "
            f"That gap is a weighting difference, not a mistake.{sample}"
        )

    if any(word in text for word in ("store", "shop", "cheaper", "swap", "kirana", "supermarket")):
        spread = ctx.get("spread")
        if spread is None or spread.empty:
            return "You have not bought the same product at two stores yet, so there is no spread to report."
        rows = "\n".join(
            f"- **{row['product']}** at {row['store_name']}: "
            f"{theme.money(row['latest_price'], currency=ctx['currency'])} "
            f"({row['vs_cheapest_pct']:+.0f}% vs. cheapest)"
            for _, row in spread.head(4).iterrows()
        )
        return f"Same product, different shelf:\n\n{rows}"

    if any(word in text for word in ("shrink", "pack", "smaller", "size", "per gram", "per kg")):
        shrink = ctx.get("shrink")
        if shrink is None or shrink.empty:
            return "No pack-size change in your receipts yet — nothing shrank without the price noticing."
        row = shrink.iloc[0]
        unit = _unit_of(row["unit_label"])
        return (
            f"**{row['product']}** went from {row['base_size']:g} {unit} to "
            f"{row['latest_size']:g} {unit} while the price moved {row['price_change_pct']:+.0f}%. "
            f"Per {row['unit_label']} that is {row['per_unit_change_pct']:+.0f}% — the "
            "shelf price hides it."
        )

    if any(word in text for word in ("spend", "spending", "month", "bill", "receipt")):
        monthly = ctx.get("spend")
        if monthly is None or monthly.empty:
            return "No spending recorded yet."
        rows = "\n".join(
            f"- {theme.month_label(row['month'])}: "
            f"{theme.money(row['spend'], decimals=0, currency=ctx['currency'])}"
            for _, row in monthly.tail(4).iterrows()
        )
        return (
            f"{ctx['receipts']} receipts across {ctx['months_tracked']} months, "
            f"averaging {_money(ctx, ctx['avg_monthly_spend'])} a month.\n\n{rows}"
        )

    country = SUPPORTED_COUNTRIES.get(
        st.session_state.get("country") or "IN", {"label": "your country"}
    )["label"]
    return (
        "I can work from your own receipts. Try **Build my plan**, or ask about your budget, "
        f"the fastest risers, pack sizes, store prices, or how you compare with {country} CPI."
    )


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #

QUICK_PROMPTS = [
    "Build my plan",
    "Am I inside budget?",
    "What got costlier?",
    "Compare with CPI?",
]


def _greeting(ctx: dict) -> str:
    if ctx.get("empty"):
        return "Add a receipt and I can start planning with your real prices."
    budget = ctx.get("budget")
    intro = (
        f"Hello {ctx['name']}. I can plan against your "
        f"{_money(ctx, budget)} budget." if budget
        else f"Hello {ctx['name']}. Set a budget in your profile and I can plan against it."
    )
    return (
        f"{intro} You have **{ctx['receipts']} receipts** over "
        f"**{ctx.get('months_tracked', 0)} months** of prices. "
        "Ask me anything, or start with the plan."
    )


def page_coach() -> None:
    ctx = build_context(st.session_state.get("months"))
    st.session_state.setdefault("chat", [{"role": "assistant", "text": _greeting(ctx)}])
    chat: list[dict] = st.session_state["chat"]

    theme.section("Your plan", "built from your receipts, not a template")

    prompt = st.chat_input("Ask about your basket, budget or plan…")
    if prompt:
        chat.append({"role": "user", "text": prompt})
        chat.append({"role": "assistant", "text": answer(prompt, ctx)})

    cols = st.columns(2)
    for index, label in enumerate(QUICK_PROMPTS):
        if cols[index % 2].button(label, key=f"quick_{label}", use_container_width=True):
            chat.append({"role": "user", "text": label})
            chat.append({"role": "assistant", "text": answer(label, ctx)})
            st.rerun()

    for message in chat:
        with st.chat_message(message["role"], avatar="🧾" if message["role"] == "assistant" else None):
            st.markdown(message["text"])

    if len(chat) > 2:
        if st.button("Clear the conversation", key="clear_chat"):
            st.session_state["chat"] = [{"role": "assistant", "text": _greeting(ctx)}]
            st.rerun()

    theme.note(
        "This coach is deterministic: it reads your basket, budget and official series and "
        "writes the same numbers you see on the charts. No language model is called."
    )
