"""Chart builders with one shared, deliberately sparse visual language.

No gridlines, no legend boxes, no chart titles: labels sit at the end of the
lines they describe, because a chart with a legend is a chart that made the
reader do work.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ui.theme import DOWN, INK, LINE, MUTED, RUST, SAGE, TEAL, UP, month_label

FONT = "Inter, -apple-system, Segoe UI, sans-serif"
SERIF = "Fraunces, Georgia, serif"


def _frame(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=18, t=14, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        showlegend=legend,
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11)),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE,
                        font=dict(color=INK, family=FONT, size=12)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=LINE,
                     ticks="outside", tickcolor="rgba(0,0,0,0)", ticklen=4,
                     automargin=True, tickfont=dict(size=11), ticklabelposition="outside")
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                     automargin=True, tickfont=dict(size=11))
    return fig


def _short(name: str, limit: int = 30) -> str:
    """Keep long product names inside the chart instead of clipping them."""
    text = str(name)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _end_label(fig: go.Figure, x, y, text: str, color: str) -> None:
    fig.add_annotation(
        x=x, y=y, text=text, showarrow=False, xanchor="left", xshift=8,
        font=dict(family=FONT, size=11, color=color),
    )


def index_chart(personal: pd.DataFrame, official: pd.DataFrame | None = None,
                height: int = 340) -> go.Figure:
    """Basket index (100 = first month) with the official series alongside."""
    fig = go.Figure()
    if personal is None or personal.empty:
        return _frame(fig, height)

    months = [month_label(month).split()[0] for month in personal["month"]]
    fig.add_trace(go.Scatter(
        x=months, y=personal["index"], mode="lines",
        line=dict(color=RUST, width=3.2, shape="spline", smoothing=0.35),
        name="Your basket",
        hovertemplate="Your basket: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=months, y=personal["index"], mode="markers",
        marker=dict(color=RUST, size=6, line=dict(color="#FFFDF8", width=1.5)),
        showlegend=False, hoverinfo="skip",
    ))

    if official is not None and not official.empty:
        official = official[official["month"].isin(personal["month"])]
        if not official.empty:
            fig.add_trace(go.Scatter(
                x=[month_label(month).split()[0] for month in official["month"]],
                y=official["index"], mode="lines",
                line=dict(color=MUTED, width=1.4, dash="dot"),
                name="Official CPI",
                hovertemplate="Official CPI: %{y:.1f}<extra></extra>",
            ))
            _end_label(fig, month_label(official["month"].iloc[-1]).split()[0],
                       float(official["index"].iloc[-1]), "official CPI", MUTED)

    _end_label(fig, months[-1], float(personal["index"].iloc[-1]),
               "your basket", RUST)

    fig.add_hline(y=100, line=dict(color=LINE, width=1))
    values = list(personal["index"])
    if official is not None and not official.empty:
        values += list(official["index"])
    low, high = min(values), max(values)
    pad = max((high - low) * 0.22, 1.5)
    fig.update_yaxes(range=[low - pad, high + pad])
    fig.update_xaxes(range=[-0.4, len(months) + 2.2])
    return _frame(fig, height)


def movers_chart(movers: pd.DataFrame, height: int | None = None) -> go.Figure:
    """Horizontal bars: what moved, worst first."""
    fig = go.Figure()
    if movers is None or movers.empty:
        return _frame(fig, height or 300)
    frame = movers.sort_values("change_pct", ascending=True).tail(8).copy()
    frame["label"] = [_short(name) for name in frame["product"]]
    colors = [RUST if value > 0 else SAGE for value in frame["change_pct"]]
    fig.add_trace(go.Bar(
        x=frame["change_pct"], y=frame["label"], orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{value:+.1f}%" for value in frame["change_pct"]],
        textposition="outside",
        textfont=dict(family=FONT, size=11, color=INK),
        hovertemplate="%{y}<br>%{x:+.1f}%<extra></extra>",
        width=0.55,
    ))
    peak = float(frame["change_pct"].abs().max() or 1)
    low = min(0.0, float(frame["change_pct"].min()))
    fig.update_xaxes(range=[low - peak * 0.05, peak * 1.32], showticklabels=False, showline=False)
    fig.update_yaxes(tickfont=dict(size=11.5, color=INK), automargin=True)
    height = height or max(220, 40 * len(frame) + 36)
    fig = _frame(fig, height)
    fig.update_layout(hovermode="closest", margin=dict(l=10, r=34, t=8, b=10))
    return fig


def spend_chart(monthly: pd.DataFrame, height: int = 220) -> go.Figure:
    fig = go.Figure()
    if monthly is None or monthly.empty:
        return _frame(fig, height)
    spends = list(monthly["spend"])
    colors = [LINE] * len(spends)
    if colors:
        colors[-1] = RUST
    fig.add_trace(go.Bar(
        x=[month_label(month).split()[0] for month in monthly["month"]],
        y=spends,
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        width=0.6,
    ))
    fig.update_xaxes(showline=True, linecolor=LINE, tickangle=0, automargin=True)
    fig.update_yaxes(showticklabels=False)
    fig = _frame(fig, height)
    fig.update_layout(margin=dict(l=10, r=14, t=10, b=34))
    return fig


def product_line(history: pd.DataFrame, height: int = 260) -> go.Figure:
    fig = go.Figure()
    if history is None or history.empty:
        return _frame(fig, height)
    frame = history.copy()
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    frame = frame.sort_values("purchase_date")
    fig.add_trace(go.Scatter(
        x=frame["purchase_date"], y=frame["unit_price"],
        mode="lines+markers",
        line=dict(color=RUST, width=2.6, shape="spline", smoothing=0.3),
        marker=dict(color=RUST, size=6, line=dict(color="#FFFDF8", width=1.5)),
        hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
    ))
    fig.update_xaxes(showline=True, linecolor=LINE, automargin=True)
    fig.update_yaxes(rangemode="tozero")
    return _frame(fig, height)


def category_chart(breakdown: pd.DataFrame, height: int = 260) -> go.Figure:
    fig = go.Figure()
    if breakdown is None or breakdown.empty:
        return _frame(fig, height)
    frame = breakdown.sort_values("change_pct")
    colors = [RUST if value > 0 else SAGE for value in frame["change_pct"]]
    fig.add_trace(go.Bar(
        x=frame["change_pct"], y=frame["category"], orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{value:+.1f}%" for value in frame["change_pct"]],
        textposition="outside",
        textfont=dict(family=FONT, size=11, color=INK),
        hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
        width=0.55,
    ))
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(tickfont=dict(size=11.5, color=INK), automargin=True)
    fig = _frame(fig, height)
    fig.update_layout(margin=dict(l=10, r=34, t=8, b=10))
    return fig


CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False}
