"""Visual system: one stylesheet, one set of formatting helpers.

The goal is that nothing on screen looks like the framework default: no
sidebar, no Streamlit toolbar, serif display type against a warm paper ground,
hairline rules instead of cards-on-cards, and tabular figures for every price.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from config import settings
from config.constants import SUPPORTED_CURRENCIES

INK = "#17211F"
MUTED = "#6E7672"
PAPER = "#FBF8F2"
PANEL = "#FFFFFF"
LINE = "#E2DCCF"
TEAL = "#1F4E5F"
UP = "#A8442B"
DOWN = "#2F6B4F"
AMBER = "#B4741F"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

:root {
  --ink: #17211F;
  --muted: #6E7672;
  --paper: #FBF8F2;
  --panel: #FFFFFF;
  --line: #E2DCCF;
  --teal: #1F4E5F;
  --up: #A8442B;
  --down: #2F6B4F;
  --amber: #B4741F;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: var(--paper) !important;
  color: var(--ink);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-feature-settings: "tnum" 1, "cv05" 1;
}

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
[data-testid="stAppViewBlockContainer"], .block-container {
  padding: 1.2rem 2.2rem 6rem;
  max-width: 1140px;
}

h1, h2, h3, h4 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 500 !important;
  letter-spacing: -0.015em;
  color: var(--ink) !important;
}
h1 { font-size: 2.1rem; }
h2 { font-size: 1.65rem; margin: 0.4rem 0 0.2rem; }
h3 { font-size: 1.25rem; }
p, li, label, .stMarkdown, .stText { color: var(--ink); }
a { color: var(--teal) !important; }
hr { border-color: var(--line); }

/* ---------- masthead ---------- */
.il-masthead {
  display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); padding-bottom: 0.7rem; margin-bottom: 0.2rem;
}
.il-wordmark {
  font-family: 'Fraunces', Georgia, serif; font-size: 1.6rem; letter-spacing: -0.03em;
  color: var(--ink);
}
.il-wordmark em { font-style: normal; color: var(--teal); }
.il-tagline { color: var(--muted); font-size: 0.86rem; }
.il-mode {
  margin-left: auto; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0.18rem 0.6rem;
  background: rgba(255,255,255,0.6);
}

/* ---------- navigation as text tabs ---------- */
div[data-testid="stRadio"] > div[role="radiogroup"] {
  gap: 1.7rem !important; padding: 0.5rem 0 0.1rem;
}
div[data-testid="stRadio"] label {
  background: transparent !important; padding: 0 0 0.45rem 0 !important;
  border-bottom: 2px solid transparent; border-radius: 0 !important;
  font-size: 0.92rem; color: var(--muted); cursor: pointer;
}
div[data-testid="stRadio"] label:hover { color: var(--ink); }
div[data-testid="stRadio"] label:has(input:checked) {
  border-bottom-color: var(--teal); color: var(--ink); font-weight: 500;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] label p { font-size: 0.92rem; }

/* ---------- hero ---------- */
.il-hero { padding: 2.2rem 0 1.2rem; border-bottom: 1px solid var(--line); }
.il-kicker {
  font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 0.5rem;
}
.il-hero-row { display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
.il-bignum {
  font-family: 'Fraunces', Georgia, serif; font-size: clamp(2.6rem, 6vw, 4.4rem);
  line-height: 0.95; letter-spacing: -0.035em; color: var(--ink);
}
.il-unit { font-size: 0.42em; margin-left: 0.12em; color: var(--muted); }
.il-hero-note { color: var(--muted); font-size: 0.95rem; max-width: 30rem; }
.il-hero-sub { margin-top: 0.7rem; color: var(--muted); font-size: 0.95rem; }
.il-hero-sub b { color: var(--ink); font-weight: 500; }

/* ---------- metric strip ---------- */
.il-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  border-bottom: 1px solid var(--line);
}
.il-kpi { padding: 1.1rem 1.2rem 1.1rem 0; border-right: 1px solid var(--line); }
.il-kpi:last-child { border-right: 0; }
.il-kpi-label { font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
.il-kpi-value {
  font-family: 'Fraunces', Georgia, serif; font-size: 1.55rem; letter-spacing: -0.02em;
  margin-top: 0.25rem; color: var(--ink);
}
.il-kpi-note { font-size: 0.8rem; color: var(--muted); margin-top: 0.15rem; }

/* ---------- section ---------- */
.il-section { display: flex; align-items: baseline; gap: 0.9rem; margin: 2.6rem 0 0.2rem; }
.il-section-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.35rem; letter-spacing: -0.01em; }
.il-section-kicker { font-size: 0.78rem; color: var(--muted); }
.il-rule { height: 1px; background: var(--line); margin: 0.55rem 0 1.1rem; }

/* ---------- chips / badges ---------- */
.il-chip {
  display: inline-block; font-size: 0.72rem; letter-spacing: 0.05em; text-transform: uppercase;
  padding: 0.12rem 0.5rem; border-radius: 999px; border: 1px solid currentColor;
  vertical-align: middle;
}
.il-chip--up { color: var(--up); }
.il-chip--down { color: var(--down); }
.il-chip--flat { color: var(--muted); }
.il-chip--sample { color: var(--amber); }

.il-note { color: var(--muted); font-size: 0.84rem; line-height: 1.5; }
.il-small { font-size: 0.82rem; color: var(--muted); }

.il-alert {
  border-left: 3px solid var(--amber); background: rgba(180,116,31,0.06);
  padding: 0.85rem 1rem; margin: 0.6rem 0;
}
.il-alert-title { font-weight: 500; font-size: 0.95rem; }
.il-alert-body { color: var(--muted); font-size: 0.86rem; margin-top: 0.15rem; }

.il-empty {
  border: 1px dashed var(--line); padding: 2rem; text-align: center;
  color: var(--muted); font-size: 0.92rem; background: rgba(255,255,255,0.45);
}

/* ---------- widgets ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  background: var(--ink); color: var(--paper); border: 1px solid var(--ink);
  border-radius: 2px; padding: 0.42rem 1.05rem; font-weight: 500; font-size: 0.88rem;
  transition: background 120ms ease, border-color 120ms ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--teal); border-color: var(--teal); color: #fff;
}
.stButton > button:focus:not(:active) { color: var(--paper); }
div[data-testid="stFileUploaderDropzone"] {
  background: rgba(255,255,255,0.5); border: 1px dashed var(--line); border-radius: 2px;
}
div[data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 2px; }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  border: 1px solid var(--line); border-radius: 2px;
}
div[data-testid="stMetricValue"] { font-family: 'Fraunces', Georgia, serif; }
.stSelectbox label, .stTextInput label, .stNumberInput label, .stDateInput label,
.stMultiSelect label, .stFileUploader label, .stTextArea label {
  font-size: 0.78rem !important; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--muted) !important;
}
div[data-testid="stAlert"] { border-radius: 2px; }

.il-foot { border-top: 1px solid var(--line); margin-top: 4rem; padding-top: 0.9rem;
  color: var(--muted); font-size: 0.78rem; }
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(value) -> str:
    return _html.escape(str(value if value is not None else ""))


def currency_symbol(currency: str | None = None) -> str:
    return SUPPORTED_CURRENCIES.get(currency or settings.DEFAULT_CURRENCY, "")


def money(value, decimals: int = 2, currency: str | None = None) -> str:
    if value is None:
        return "—"
    symbol = currency_symbol(currency)
    return f"{symbol}{float(value):,.{decimals}f}"


def compact_money(value) -> str:
    if value is None:
        return "—"
    value = float(value)
    symbol = currency_symbol()
    if abs(value) >= 100_000:
        return f"{symbol}{value / 100_000:,.1f}L"
    if abs(value) >= 1_000:
        return f"{symbol}{value / 1_000:,.1f}k"
    return f"{symbol}{value:,.0f}"


def signed(value, unit: str = "%") -> str:
    if value is None:
        return "—"
    return f"{float(value):+.1f}{unit}"


def chip(value, unit: str = "%") -> str:
    if value is None:
        return '<span class="il-chip il-chip--flat">no data</span>'
    value = float(value)
    if value > 0.05:
        return f'<span class="il-chip il-chip--up">{value:+.1f}{unit}</span>'
    if value < -0.05:
        return f'<span class="il-chip il-chip--down">{value:+.1f}{unit}</span>'
    return f'<span class="il-chip il-chip--flat">{value:+.1f}{unit}</span>'


def month_label(period: str) -> str:
    """'2026-03' -> 'Mar 2026'."""
    try:
        year, month = str(period).split("-")[:2]
        names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{names[int(month)]} {year}"
    except (ValueError, IndexError):
        return str(period)


def masthead(mode_label: str) -> None:
    st.markdown(
        f"""
        <div class="il-masthead">
          <div class="il-wordmark">Inflation<em>Lens</em></div>
          <div class="il-tagline">Your groceries. Your prices. Your real inflation.</div>
          <div class="il-mode">{esc(mode_label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, kicker: str = "") -> None:
    st.markdown(
        f"""
        <div class="il-section">
          <span class="il-section-title">{esc(title)}</span>
          <span class="il-section-kicker">{esc(kicker)}</span>
        </div>
        <div class="il-rule"></div>
        """,
        unsafe_allow_html=True,
    )


def hero(kicker: str, value: str, note: str, sub: str = "", unit: str = "%") -> None:
    st.markdown(
        f"""
        <div class="il-hero">
          <div class="il-kicker">{esc(kicker)}</div>
          <div class="il-hero-row">
            <span class="il-bignum">{esc(value)}<span class="il-unit">{esc(unit)}</span></span>
            <span class="il-hero-note">{note}</span>
          </div>
          {f'<div class="il-hero-sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple[str, str, str]]) -> None:
    cells = "".join(
        f"""
        <div class="il-kpi">
          <div class="il-kpi-label">{esc(label)}</div>
          <div class="il-kpi-value">{esc(value)}</div>
          <div class="il-kpi-note">{esc(note)}</div>
        </div>
        """
        for label, value, note in items
    )
    st.markdown(f'<div class="il-kpis">{cells}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="il-note">{text}</div>', unsafe_allow_html=True)


def alert(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="il-alert">
          <div class="il-alert-title">{esc(title)}</div>
          <div class="il-alert-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty(message: str, hint: str = "") -> None:
    st.markdown(
        f'<div class="il-empty">{esc(message)}'
        f'{f"<br><span class=\'il-small\'>{esc(hint)}</span>" if hint else ""}</div>',
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        '<div class="il-foot">Personal price history kept on this machine. '
        'Not financial advice; prices are what the receipts said.</div>',
        unsafe_allow_html=True,
    )
