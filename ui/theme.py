"""Visual system: one stylesheet, one set of formatting helpers.

The look borrows from printed grocery packaging rather than from dashboards:
warm cream paper, terracotta ink, a wobbly display serif, lilac bands and
sticker badges. Everything is emitted as *one line* of HTML because markdown
treats indented markup as a code block — which is exactly how the metric strip
ended up printing its own source on screen.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from config import settings
from config.constants import SUPPORTED_CURRENCIES

INK = "#2F2A20"
MUTED = "#6B6355"
PAPER = "#FBF3E4"
SAND = "#F3E7D2"
PANEL = "#FFFDF8"
LINE = "#E3D8C3"
RUST = "#B4401E"
SAGE = "#6F7F52"
LILAC = "#CDC2E6"
LILAC_SOFT = "#E6DFF4"

# Kept for callers that imported the older names.
TEAL = RUST
UP = RUST
DOWN = SAGE

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT,WONK@9..144,400..900,0..100,0..1&family=Inter:wght@400;500;600&display=swap');

:root {
  --ink: #2F2A20;
  --muted: #6B6355;
  --paper: #FBF3E4;
  --sand: #F3E7D2;
  --panel: #FFFDF8;
  --line: #E3D8C3;
  --rust: #B4401E;
  --sage: #6F7F52;
  --lilac: #CDC2E6;
  --lilac-soft: #E6DFF4;
  --radius: 26px;
}

.stApp, [data-testid="stAppViewContainer"] {
  background: var(--paper) !important;
  color: var(--ink);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-feature-settings: "tnum" 1;
}
[data-testid="stHeader"] { background: transparent !important; height: 0; }
[data-testid="stToolbar"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu, footer {
  display: none !important;
}

/* The toolbar is hidden, but its expand button is the only way back into a
   collapsed sidebar: keep exactly that one control, as a floating pill. */
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stToolbar"] {
  display: flex !important; position: fixed; top: 0.7rem; left: 0.75rem; z-index: 1000;
  height: auto; padding: 0 !important; background: transparent !important;
}
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stExpandSidebarButton"] {
  display: flex !important; align-items: center; justify-content: center;
  width: 2.4rem; height: 2.4rem; border-radius: 999px;
  background: var(--panel) !important; border: 1px solid var(--line) !important;
  color: var(--ink) !important; box-shadow: 0 6px 18px rgba(47,42,32,0.10);
  transition: background 160ms ease, color 160ms ease, transform 160ms ease;
}
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stExpandSidebarButton"]:hover {
  background: var(--rust) !important; border-color: var(--rust) !important;
  color: #FFF4EA !important; transform: translateY(-1px);
}
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stExpandSidebarButton"] span {
  color: inherit !important;
}
@media (max-width: 780px) {
  /* On a phone the pill bar already reaches every screen (and **You** can sign
     out), so the floating handle would only sit on top of it. */
  body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stToolbar"] {
    display: none !important;
  }
}
[data-testid="stAppViewBlockContainer"], .block-container {
  padding: 1.1rem 2.4rem 4rem;
  max-width: 1140px;
}

h1, h2, h3, h4 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 600 !important;
  font-variation-settings: "SOFT" 70, "WONK" 1, "opsz" 96;
  letter-spacing: -0.02em;
  color: var(--ink) !important;
}
h1 { font-size: 2rem; }
h2 { font-size: 1.6rem; }
h3 { font-size: 1.2rem; }
p, li, label, .stMarkdown, .stText { color: var(--ink); }
a { color: var(--rust) !important; }
hr { border-color: var(--line); }
::selection { background: var(--lilac); color: var(--ink); }

/* ---------------- motion ---------------- */
@keyframes il-rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}
@keyframes il-pop {
  0% { opacity: 0; transform: translateY(16px) scale(0.98); }
  100% { opacity: 1; transform: none; }
}
@keyframes il-grow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
@keyframes il-draw {
  from { stroke-dashoffset: 240; }
  to { stroke-dashoffset: 0; }
}
@keyframes il-tilt {
  0%, 100% { rotate: -7deg; }
  50% { rotate: 1.5deg; }
}
@keyframes il-bob {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(-14px, 16px, 0) scale(1.06); }
}
@keyframes il-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(111, 127, 82, 0.5); }
  50% { box-shadow: 0 0 0 4px rgba(111, 127, 82, 0); }
}
@keyframes il-nudge {
  0%, 93%, 100% { transform: none; }
  96% { transform: translateY(-2px); }
}

/* ---------------- sidebar ---------------- */
[data-testid="stSidebar"] {
  background: var(--sand) !important;
  border-right: 1px solid var(--line);
  width: 285px !important;
  min-width: 285px !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }
[data-testid="stSidebarUserContent"] { padding: 1.5rem 1.15rem 1.5rem; }
[data-testid="stSidebar"] hr { border-color: rgba(47,42,32,0.1); margin: 0.9rem 0; }
[data-testid="stSidebarCollapseButton"] button { color: var(--ink) !important; }

.il-brand { padding-bottom: 0.2rem; }
.il-wordmark {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 80, "WONK" 1, "opsz" 120;
  font-weight: 700; font-size: 1.72rem; line-height: 1; letter-spacing: -0.035em;
  color: var(--ink);
}
.il-wordmark em { font-style: normal; color: var(--rust); }
.il-tagline {
  margin-top: 0.45rem; color: var(--muted); font-size: 0.79rem; line-height: 1.4;
  max-width: 13rem;
}
.il-mode {
  display: inline-block; margin-top: 0.7rem; font-size: 0.64rem; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--ink); background: var(--lilac);
  border-radius: 999px; padding: 0.2rem 0.6rem;
}
.il-mode:not(.il-mode--guest)::before {
  content: ""; display: inline-block; width: 6px; height: 6px; margin-right: 0.38rem;
  border-radius: 50%; background: var(--sage); vertical-align: 1px;
  animation: il-pulse 2.6s ease-in-out infinite;
}
.il-mode--guest {
  background: transparent; border: 1px solid var(--line); color: var(--muted);
  margin-left: 0.25rem;
}
.il-side-label {
  font-size: 0.64rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin: 1.1rem 0 0.45rem;
}
.il-side-foot {
  margin-top: 1.4rem; padding-top: 0.9rem; border-top: 1px solid rgba(47,42,32,0.1);
  color: var(--muted); font-size: 0.74rem; line-height: 1.5;
}
.il-side-foot b { color: var(--ink); font-weight: 500; }

/* ---------------- buttons ---------------- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  font-family: 'Inter', sans-serif; font-weight: 500; font-size: 0.9rem;
  border-radius: 999px !important; border: 1px solid var(--line);
  background: transparent; color: var(--ink);
  padding: 0.45rem 1.1rem !important; transition: all 140ms ease;
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color: var(--ink); background: rgba(255,255,255,0.7); color: var(--ink);
  transform: translateY(-1px); box-shadow: 0 6px 16px rgba(47,42,32,0.10);
}
.stButton button:active, .stDownloadButton button:active, .stFormSubmitButton button:active {
  transform: translateY(0) scale(0.985);
}
.st-key-navlist button[kind="primary"] {
  animation: il-pop 320ms cubic-bezier(.2,.75,.25,1) both;
}
[data-testid="stBaseButton-primary"], .stButton button[kind="primary"] {
  background: var(--rust) !important; border-color: var(--rust) !important;
  color: #FFF4EA !important;
}
[data-testid="stBaseButton-primary"]:hover, .stButton button[kind="primary"]:hover {
  background: #98351A !important; border-color: #98351A !important; color: #FFF4EA !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] .stButton button[kind="secondary"] {
  background: transparent !important; border-color: transparent !important;
}
.stDownloadButton button, .stFormSubmitButton button[kind="secondary"] {
  border: 1px solid var(--ink) !important; color: var(--ink) !important;
}

/* sidebar navigation: stacked pills, left aligned */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.45rem; }
[data-testid="stSidebar"] [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
.st-key-navlist [data-testid="stVerticalBlock"],
.st-key-windowgrid [data-testid="stVerticalBlock"],
.st-key-windowgrid [data-testid="stHorizontalBlock"] { gap: 0.15rem !important; }
.st-key-navlist .stButton button {
  width: 100%; justify-content: flex-start !important; text-align: left !important;
  padding: 0.46rem 1rem !important; font-size: 0.93rem; border-radius: 999px !important;
  display: flex !important;
}
.st-key-navlist .stButton button > div {
  justify-content: flex-start !important; text-align: left !important;
  width: 100%; margin: 0 !important;
}
.st-key-navlist .stButton button p {
  font-size: 0.93rem !important; text-align: left !important; margin: 0 !important;
}
.st-key-navlist .stButton button[kind="secondary"] { color: var(--ink) !important; }
.st-key-navlist .stButton button[kind="secondary"]:hover {
  background: rgba(255,255,255,0.75) !important;
}
.st-key-windowgrid .stButton button {
  width: 100%; justify-content: center !important; padding: 0.35rem 0.4rem !important;
  font-size: 0.78rem; letter-spacing: 0.02em;
}
.st-key-windowgrid .stButton button p { font-size: 0.78rem !important; }

/* ---------------- hero ---------------- */
.il-hero {
  position: relative; overflow: hidden;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 2.1rem 2.3rem 2rem; margin: 1.1rem 0 1.3rem;
  animation: il-rise 620ms cubic-bezier(.2,.75,.25,1) both;
}
.il-hero::before {
  content: ""; position: absolute; right: -70px; top: -110px; width: 330px; height: 330px;
  border-radius: 50%; background: var(--lilac-soft); opacity: 0.8;
  animation: il-bob 16s ease-in-out infinite;
}
.il-hero-copy { position: relative; z-index: 1; max-width: 34rem; }
.il-kicker {
  font-size: 0.68rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 0.6rem;
}
.il-bignum {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 90, "WONK" 1, "opsz" 144;
  font-weight: 700; font-size: clamp(3.4rem, 7vw, 5.4rem); line-height: 0.86;
  letter-spacing: -0.04em; color: var(--rust); display: block;
  animation: il-pop 680ms cubic-bezier(.2,.75,.25,1) both;
}
.il-unit { font-size: 0.34em; margin-left: 0.14em; color: var(--muted); font-weight: 500; }
.il-squiggle { display: block; margin: 0.75rem 0 0.85rem; }
.il-squiggle path {
  stroke-dasharray: 240; animation: il-draw 900ms 180ms ease both;
}
.il-hero-note { color: var(--ink); font-size: 0.98rem; line-height: 1.5; max-width: 26rem; }
.il-hero-sub { margin-top: 0.6rem; color: var(--muted); font-size: 0.92rem; }
.il-hero-sub b { color: var(--ink); font-weight: 600; }

.il-sticker {
  position: absolute; right: 2.4rem; top: 50%; transform: translateY(-50%);
  width: 142px; height: 142px; z-index: 2; rotate: -7deg;
  animation: il-tilt 11s ease-in-out infinite;
}
@media (max-width: 780px) { .il-sticker { display: none; } }

/* ---------------- metric band ---------------- */
.il-kpis {
  display: grid; grid-template-columns: repeat(4, 1fr);
  background: var(--lilac-soft); border-radius: var(--radius);
  padding: 0.3rem 0.5rem; margin: 0 0 1.7rem;
}
.il-kpi {
  padding: 1.15rem 1.35rem; border-right: 1px solid rgba(47,42,32,0.14);
  animation: il-rise 520ms cubic-bezier(.2,.75,.25,1) both;
  transition: background 180ms ease;
}
.il-kpi:hover { background: rgba(255,253,248,0.45); }
.il-kpi:nth-child(2) { animation-delay: 70ms; }
.il-kpi:nth-child(3) { animation-delay: 140ms; }
.il-kpi:nth-child(4) { animation-delay: 210ms; }
.il-kpi:last-child { border-right: 0; }
.il-kpi-label {
  font-size: 0.64rem; letter-spacing: 0.14em; text-transform: uppercase; color: #6B6355;
}
.il-kpi-value {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 70, "WONK" 1, "opsz" 90;
  font-weight: 600; font-size: 1.5rem; letter-spacing: -0.025em;
  margin-top: 0.3rem; color: var(--ink);
}
.il-kpi-note { font-size: 0.78rem; color: #6B6355; margin-top: 0.15rem; }
@media (max-width: 900px) {
  .il-kpis { grid-template-columns: repeat(2, 1fr); }
  .il-kpi:nth-child(2) { border-right: 0; }
  .il-kpi:nth-child(1), .il-kpi:nth-child(2) { border-bottom: 1px solid rgba(47,42,32,0.14); }
}

/* ---------------- sections ---------------- */
.il-section {
  display: flex; align-items: baseline; gap: 0.9rem; flex-wrap: wrap;
  margin: 2.1rem 0 0.35rem;
  animation: il-rise 440ms cubic-bezier(.2,.75,.25,1) both;
}
.il-section-title {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 70, "WONK" 1, "opsz" 100;
  font-weight: 600; font-size: 1.32rem; letter-spacing: -0.015em; color: var(--ink);
}
.il-section-kicker { font-size: 0.76rem; color: var(--muted); }
.il-rule {
  height: 1px; background: var(--line); margin: 0.5rem 0 1rem;
  transform-origin: left center; animation: il-grow 620ms cubic-bezier(.2,.75,.25,1) both;
}

/* ---------------- chips, notes, alerts ---------------- */
.il-chip {
  display: inline-block; font-size: 0.64rem; letter-spacing: 0.09em; text-transform: uppercase;
  padding: 0.16rem 0.5rem; border-radius: 999px; border: 1px solid currentColor;
  vertical-align: middle; font-weight: 500;
}
.il-chip--up { color: var(--rust); background: #FBEDE4; border-color: #EBC9B6; }
.il-chip--down { color: var(--sage); background: #EDF1E4; border-color: #CBD3B4; }
.il-chip--flat { color: var(--muted); }
.il-chip--sample {
  color: var(--ink); background: var(--lilac); border-color: var(--lilac);
  animation: il-nudge 6s ease-in-out infinite;
}

.il-note { color: var(--muted); font-size: 0.84rem; line-height: 1.55; }
.il-note b { color: var(--ink); }
.il-note code {
  background: var(--sand); padding: 0.05rem 0.3rem; border-radius: 4px;
  font-size: 0.8rem; color: var(--ink);
}
.il-small { font-size: 0.82rem; color: var(--muted); }

.il-alert {
  border: 1px solid #EBC9B6; border-left: 4px solid var(--rust);
  background: #FBEDE4; border-radius: 0 18px 18px 0;
  padding: 0.9rem 1.1rem; margin: 0.7rem 0;
  animation: il-rise 480ms cubic-bezier(.2,.75,.25,1) both;
}
.il-alert-title {
  font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 1rem; color: var(--ink);
}
.il-alert-body { color: #6B6355; font-size: 0.85rem; margin-top: 0.2rem; line-height: 1.5; }

.il-empty {
  border: 1px dashed #D8CBB2; border-radius: 20px; padding: 2.2rem 1.5rem;
  text-align: center; color: var(--muted); font-size: 0.92rem;
  background: rgba(255,253,248,0.6);
  animation: il-rise 480ms cubic-bezier(.2,.75,.25,1) both;
}

/* ---------------- numbered steps ---------------- */
.il-steps {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.9rem; margin: 1.6rem 0 0;
}
.il-step {
  background: var(--panel); border: 1px solid var(--line); border-radius: 20px;
  padding: 1.2rem 1.2rem 1.3rem;
  animation: il-rise 540ms cubic-bezier(.2,.75,.25,1) both;
  transition: transform 180ms ease, box-shadow 180ms ease;
}
.il-step:hover { transform: translateY(-3px); box-shadow: 0 12px 26px rgba(47,42,32,0.09); }
.il-step:nth-child(2) { animation-delay: 80ms; }
.il-step:nth-child(3) { animation-delay: 160ms; }
.il-step-n { transition: background 180ms ease, color 180ms ease; }
.il-step:hover .il-step-n { background: var(--rust); color: #FFF4EA; }
.il-step-n {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.9rem; height: 1.9rem; border-radius: 999px; background: var(--lilac);
  font-family: 'Fraunces', Georgia, serif; font-weight: 700; font-size: 0.95rem;
  color: var(--ink); margin-bottom: 0.7rem;
}
.il-step-t {
  font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 1.02rem;
  color: var(--ink); letter-spacing: -0.01em;
}
.il-step-d { color: var(--muted); font-size: 0.82rem; line-height: 1.5; margin-top: 0.25rem; }
@media (max-width: 900px) { .il-steps { grid-template-columns: 1fr; } }

/* ---------------- charts, tables, widgets ---------------- */
[data-testid="stPlotlyChart"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 22px;
  padding: 0.4rem 0.5rem; overflow: hidden;
  animation: il-rise 560ms cubic-bezier(.2,.75,.25,1) both;
  transition: transform 200ms ease, box-shadow 200ms ease;
}
[data-testid="stPlotlyChart"]:hover {
  transform: translateY(-3px); box-shadow: 0 12px 28px rgba(47,42,32,0.10);
}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border: 1px solid var(--line); border-radius: 16px; overflow: hidden;
  animation: il-rise 520ms cubic-bezier(.2,.75,.25,1) both;
}
[data-testid="stAlert"] { animation: il-rise 420ms ease both; }
[data-testid="stExpander"] details {
  border: 1px solid var(--line); border-radius: 16px; background: rgba(255,253,248,0.6);
}
[data-testid="stFileUploaderDropzone"] {
  background: rgba(255,253,248,0.65); border: 1px dashed #D8CBB2; border-radius: 18px;
}
[data-testid="stAlert"] { border-radius: 16px; }

/* pill radio (source pickers in the body) */
div[data-testid="stRadio"] > div[role="radiogroup"] {
  gap: 0.4rem; padding: 0.15rem 0 0.6rem; flex-wrap: wrap;
}
div[data-testid="stRadio"] label {
  background: transparent !important; border: 1px solid var(--line); border-radius: 999px;
  padding: 0.3rem 0.95rem !important; color: var(--muted);
  cursor: pointer; transition: all 140ms ease;
}
div[data-testid="stRadio"] label:hover { border-color: var(--ink); }
div[data-testid="stRadio"] label:has(input:checked),
div[data-testid="stRadio"] label[data-selected="true"] {
  background: var(--ink) !important; border-color: var(--ink);
}
div[data-testid="stRadio"] label:has(input:checked) p,
div[data-testid="stRadio"] label[data-selected="true"] p { color: var(--paper) !important; }
/* hide only the inline radio dot, never the text wrapper */
div[data-testid="stRadio"] label > div > div:first-child { display: none !important; }
div[data-testid="stRadio"] label > div { align-items: center; }
div[data-testid="stRadio"] label p { font-size: 0.86rem; margin: 0 !important; color: inherit; }

.stSelectbox label, .stTextInput label, .stNumberInput label, .stDateInput label,
.stMultiSelect label, .stFileUploader label, .stTextArea label, .stSlider label {
  font-size: 0.68rem !important; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted) !important;
}
[data-baseweb="select"] > div, [data-baseweb="input"] {
  border-radius: 12px !important; background: var(--panel) !important;
}

.il-foot {
  border-top: 1px solid var(--line); margin-top: 3.5rem; padding-top: 0.9rem;
  color: var(--muted); font-size: 0.76rem; letter-spacing: 0.01em;
  animation: il-rise 520ms ease both;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}

/* ---------------- account, auth, profile, chat ---------------- */
.il-account { display: flex; gap: 0.7rem; align-items: center; }
.il-avatar {
  border-radius: 50%; object-fit: cover; border: 1px solid var(--line);
  background: var(--lilac-soft); flex: 0 0 auto;
}
.il-avatar--initials {
  display: flex; align-items: center; justify-content: center;
  font-family: 'Fraunces', Georgia, serif; font-weight: 700; color: var(--ink);
}
.il-account-copy { min-width: 0; }
.il-account-name {
  font-family: 'Fraunces', Georgia, serif; font-variation-settings: "SOFT" 70, "WONK" 1;
  font-size: 1.04rem; font-weight: 600; line-height: 1.15; color: var(--ink);
}
.il-account-mail {
  font-size: 0.7rem; color: var(--muted); max-width: 10.5rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.il-account-chips { margin-top: 0.65rem; }
.il-account-chips .il-mode { margin-top: 0.25rem; }

.il-auth-aside {
  position: relative; overflow: hidden; background: var(--panel);
  border: 1px solid var(--line); border-radius: var(--radius);
  padding: 2.2rem 2rem; min-height: 30rem;
  animation: il-rise 620ms cubic-bezier(.2,.75,.25,1) both;
}
.il-auth-aside::before {
  content: ""; position: absolute; right: -90px; bottom: -80px; width: 300px; height: 300px;
  border-radius: 50%; background: var(--lilac-soft); opacity: 0.75;
  animation: il-bob 17s ease-in-out infinite;
}
.il-auth-line {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 80, "WONK" 1, "opsz" 100;
  font-size: 1.28rem; line-height: 1.3; margin: 0.75rem 0 1.5rem; max-width: 17rem;
}
.il-auth-points {
  display: grid; gap: 0.85rem; font-size: 0.86rem; line-height: 1.55;
  color: var(--muted); max-width: 21rem; position: relative; z-index: 1;
}
.il-auth-points b { color: var(--ink); font-weight: 600; }
.il-auth-aside .il-sticker {
  right: 20px; bottom: 18px; top: auto; transform: none; width: 118px; height: 118px;
  opacity: 0.95;
}
@media (max-width: 780px) { .il-auth-aside { min-height: 0; padding: 1.5rem 1.3rem; } }

.st-key-authcard {
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.5rem 1.5rem 1.1rem;
  animation: il-rise 680ms cubic-bezier(.2,.75,.25,1) both;
}
.st-key-authcard .stButton button { width: 100%; }

.st-key-profile_card, .st-key-profile_form_card {
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.5rem 1.5rem 1.2rem;
  animation: il-rise 480ms cubic-bezier(.2,.75,.25,1) both;
}
.il-profile-name {
  font-family: 'Fraunces', Georgia, serif;
  font-variation-settings: "SOFT" 80, "WONK" 1;
  font-size: 1.22rem; font-weight: 600; margin-top: 0.85rem; line-height: 1.15;
  overflow-wrap: anywhere;
}
.il-profile-mail {
  color: var(--muted); font-size: 0.74rem; margin-bottom: 1.1rem;
  overflow-wrap: anywhere;
}
.il-avatar-wrap { text-align: center; margin-top: 0.2rem; }
.il-avatar-wrap .il-avatar { display: inline-flex; }
.il-form-title {
  font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 1.12rem;
  margin-bottom: 0.7rem;
}

[data-testid="stChatMessage"] { background: transparent; padding: 0.3rem 0; }
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 18px;
  padding: 0.85rem 1.1rem; animation: il-rise 320ms ease both;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p { margin-bottom: 0.4rem; }
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }
[data-testid="stChatInput"] {
  background: var(--panel) !important; border: 1px solid var(--line) !important;
  border-radius: 999px !important; box-shadow: 0 6px 18px rgba(47,42,32,0.06);
}
[data-testid="stChatInput"] textarea { color: var(--ink) !important; }
[data-testid="stBottom"] > div { background: var(--paper) !important; }

/* mobile control bar: hidden on desktop */
.st-key-mobilenav { display: none; }

/* ---------------- small screens ---------------- */
@media (max-width: 780px) {
  .st-key-mobilenav { display: block; margin: 0.1rem 0 0.8rem; }
  .st-key-mobilenav [data-testid="stPills"] > div[role="group"],
  .st-key-mobilenav [role="group"] {
    flex-wrap: wrap !important; gap: 0.3rem !important; overflow: visible !important;
  }
  .st-key-mobilenav [data-testid="stPills"] button {
    border-radius: 999px !important; border: 1px solid var(--line) !important;
    background: transparent !important; color: var(--ink) !important;
    font-size: 0.78rem !important; line-height: 1.1 !important;
    padding: 0.28rem 0.75rem !important; min-height: 0 !important;
  }
  .st-key-mobilenav [data-testid="stPills"] button[kind="pillsActive"],
  .st-key-mobilenav [data-testid="stPills"] button[aria-checked="true"],
  .st-key-mobilenav [data-testid="stPills"] button[aria-selected="true"] {
    background: var(--rust) !important; border-color: var(--rust) !important;
    color: #FFF4EA !important;
  }
  .st-key-mobilenav [data-testid="stPills"] button p {
    font-size: 0.78rem !important; margin: 0 !important;
  }
  [data-testid="stAppViewBlockContainer"], .block-container {
    padding: 0.6rem 1.1rem 3rem;
  }
  .il-hero { padding: 1.5rem 1.35rem 1.6rem; border-radius: 22px; }
  .il-bignum { font-size: clamp(2.8rem, 16vw, 4rem); }
  .il-kpi { padding: 0.95rem 1rem; }
  .il-kpis { border-radius: 20px; }
  .il-section { margin-top: 1.7rem; }
  .il-section-title { font-size: 1.15rem; }
}
</style>
"""

_SQUIGGLE = (
    '<svg class="il-squiggle" width="118" height="12" viewBox="0 0 118 12" fill="none" '
    'aria-hidden="true"><path d="M2 7.5C10 1.5 16 1.5 24 7.5S38 13.5 46 7.5 60 1.5 68 7.5'
    ' 82 13.5 90 7.5 104 1.5 116 6.5" stroke="#B4401E" stroke-width="2.4" '
    'stroke-linecap="round"/></svg>'
)


def _blk(markup: str) -> str:
    """Collapse markup to one line so markdown cannot read it as a code block."""
    return " ".join(part for part in (line.strip() for line in markup.splitlines()) if part)


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(value) -> str:
    return _html.escape(str(value if value is not None else ""))


def currency_symbol(currency: str | None = None) -> str:
    if currency is None:
        user = st.session_state.get("user") or {}
        currency = user.get("currency")
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


def avatar(user: dict | None, size: int = 44) -> str:
    """A round picture, or the person's initials in the same shape."""
    if not user:
        return ""
    name = esc(user.get("name") or "?")
    source = user.get("avatar")
    style = f"width:{size}px; height:{size}px;"
    if source:
        return f'<img class="il-avatar" src="{source}" alt="{name}" style="{style}">'
    initials = "".join(part[0] for part in str(user.get("name") or "?").split()[:2])
    return (
        f'<div class="il-avatar il-avatar--initials" style="{style} '
        f'font-size:{max(12, size // 3)}px">{esc(initials.upper() or "?")}</div>'
    )


def account(user: dict, mode_label: str) -> None:
    """Sidebar masthead: the signed-in person, then their mode and budget."""
    budget = user.get("monthly_budget")
    budget_chip = (
        f'<span class="il-mode il-mode--guest">{money(budget, decimals=0, currency=user.get("currency"))}'
        f' budget</span>'
        if budget else
        '<span class="il-mode il-mode--guest">no budget set</span>'
    )
    st.markdown(
        _blk(f"""
        <div class="il-brand">
          <div class="il-account">
            {avatar(user, 46)}
            <div class="il-account-copy">
              <div class="il-account-name">{esc(user.get('name'))}</div>
              <div class="il-account-mail">{esc(user.get('email'))}</div>
            </div>
          </div>
          <div class="il-account-chips">
            <span class="il-mode">{esc(mode_label)}</span>{budget_chip}
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def side_label(text: str) -> None:
    st.markdown(f'<div class="il-side-label">{esc(text)}</div>', unsafe_allow_html=True)


def side_foot(markup: str) -> None:
    st.markdown(f'<div class="il-side-foot">{markup}</div>', unsafe_allow_html=True)


def section(title: str, kicker: str = "") -> None:
    st.markdown(
        _blk(f"""
        <div class="il-section">
          <span class="il-section-title">{esc(title)}</span>
          <span class="il-section-kicker">{esc(kicker)}</span>
        </div>
        <div class="il-rule"></div>
        """),
        unsafe_allow_html=True,
    )


def _sticker() -> str:
    """A printed sticker: ring of type around a receipt mark."""
    return (
        '<svg class="il-sticker" viewBox="0 0 132 132" aria-hidden="true">'
        '<defs><path id="il-circle" d="M66,66 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0"/></defs>'
        f'<circle cx="66" cy="66" r="64" fill="{LILAC}"/>'
        f'<circle cx="66" cy="66" r="52" fill="none" stroke="{INK}" stroke-width="0.8" opacity="0.3"/>'
        f'<text font-family="Inter, sans-serif" font-size="8" letter-spacing="1.7" fill="{INK}">'
        '<textPath href="#il-circle" startOffset="2">REAL PRICES · REAL RECEIPTS · </textPath></text>'
        f'<g fill="none" stroke="{INK}" stroke-width="2.1" stroke-linecap="round" '
        'stroke-linejoin="round">'
        '<path d="M57 49h18v30l-4.5-3.2-4.5 3.2-4.5-3.2-4.5 3.2z"/>'
        '<path d="M61.5 58h9M61.5 64h9M61.5 70h5.5"/>'
        '</g>'
        '</svg>'
    )


def hero(kicker: str, value: str, note: str, sub: str = "", unit: str = "%") -> None:
    st.markdown(
        _blk(f"""
        <div class="il-hero">
          <div class="il-hero-copy">
            <div class="il-kicker">{esc(kicker)}</div>
            <span class="il-bignum">{esc(value)}<span class="il-unit">{esc(unit)}</span></span>
            {_SQUIGGLE}
            <div class="il-hero-note">{note}</div>
            {f'<div class="il-hero-sub">{sub}</div>' if sub else ''}
          </div>
          {_sticker()}
        </div>
        """),
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple[str, str, str]]) -> None:
    cells = "".join(
        f'<div class="il-kpi"><div class="il-kpi-label">{esc(label)}</div>'
        f'<div class="il-kpi-value">{esc(value)}</div>'
        f'<div class="il-kpi-note">{esc(note)}</div></div>'
        for label, value, note in items
    )
    st.markdown(f'<div class="il-kpis">{cells}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="il-note">{_blk(text)}</div>', unsafe_allow_html=True)


def alert(title: str, body: str) -> None:
    st.markdown(
        f'<div class="il-alert"><div class="il-alert-title">{esc(title)}</div>'
        f'<div class="il-alert-body">{_blk(body)}</div></div>',
        unsafe_allow_html=True,
    )


def steps(items: list[tuple[str, str]]) -> None:
    """Numbered how-it-works cards, for screens that start blank."""
    cards = "".join(
        f'<div class="il-step"><div class="il-step-n">{index}</div>'
        f'<div class="il-step-t">{esc(title)}</div>'
        f'<div class="il-step-d">{esc(body)}</div></div>'
        for index, (title, body) in enumerate(items, start=1)
    )
    st.markdown(f'<div class="il-steps">{cards}</div>', unsafe_allow_html=True)


def empty(message: str, hint: str = "") -> None:
    tail = f'<br><span class="il-small">{esc(hint)}</span>' if hint else ""
    st.markdown(f'<div class="il-empty">{esc(message)}{tail}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        '<div class="il-foot">Price history kept with your account. '
        'Not financial advice; prices are what the receipts said.</div>',
        unsafe_allow_html=True,
    )
