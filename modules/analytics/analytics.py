"""Personal price history, inflation, basket index and comparison helpers.

Every calculation works on one tidy DataFrame:

    receipt_id, purchase_date, product, product_id, category, brand,
    package_size, package_unit, quantity, unit_price, total_price, store_name

so the SQLite path and the in-session demo path produce identical numbers.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from modules.data_management.models import CPIData, Product, PurchaseItem, Receipt

HISTORY_COLUMNS = [
    "receipt_id", "purchase_date", "product", "product_id", "category", "brand",
    "package_size", "package_unit", "quantity", "unit_price", "total_price",
    "store_name",
]


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def months_ago(months: int, today: date | None = None) -> date:
    today = today or date.today()
    year, month = today.year, today.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def personal_price_history(
    session: Session, months: int | None = None, today: date | None = None
) -> pd.DataFrame:
    query = (
        select(
            Receipt.receipt_id,
            Receipt.purchase_date,
            Product.product_name,
            Product.product_id,
            Product.category,
            Product.brand,
            PurchaseItem.package_size,
            PurchaseItem.unit,
            PurchaseItem.quantity,
            PurchaseItem.unit_price,
            PurchaseItem.total_price,
            Receipt.store_name,
        )
        .join(PurchaseItem, PurchaseItem.receipt_id == Receipt.receipt_id)
        .join(Product, PurchaseItem.product_id == Product.product_id)
        .where(PurchaseItem.verification_status == "verified")
        .order_by(Receipt.purchase_date)
    )
    if months:
        query = query.where(Receipt.purchase_date >= months_ago(months, today))

    rows = session.execute(query).all()
    if not rows:
        return _empty_history()

    frame = pd.DataFrame(rows, columns=[
        "receipt_id", "purchase_date", "product", "product_id", "category",
        "brand", "package_size", "package_unit", "quantity", "unit_price",
        "total_price", "store_name",
    ])
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    return frame[HISTORY_COLUMNS]


def history_from_receipts(
    receipts: list[dict], months: int | None = None, today: date | None = None
) -> pd.DataFrame:
    """Flatten the in-session demo receipts into the same tidy frame."""
    rows = []
    cutoff = months_ago(months, today) if months else None
    for index, receipt in enumerate(receipts, start=1):
        purchase_date = receipt.get("purchase_date")
        if cutoff and purchase_date and purchase_date < cutoff:
            continue
        for item in receipt.get("items", []):
            quantity = float(item.get("quantity") or 1)
            unit_price = item.get("unit_price")
            total_price = item.get("total_price")
            if unit_price is None and total_price is not None:
                unit_price = total_price / quantity if quantity else total_price
            rows.append({
                "receipt_id": receipt.get("receipt_id", index),
                "purchase_date": pd.Timestamp(purchase_date),
                "product": item.get("product"),
                "product_id": None,
                "category": item.get("category"),
                "brand": item.get("brand"),
                "package_size": item.get("package_size"),
                "package_unit": item.get("package_unit"),
                "quantity": quantity,
                "unit_price": float(unit_price or 0),
                "total_price": float(total_price if total_price is not None else unit_price or 0),
                "store_name": receipt.get("store_name"),
            })
    if not rows:
        return _empty_history()
    return pd.DataFrame(rows, columns=HISTORY_COLUMNS)


def monthly_prices(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["product", "month", "price"])
    frame = history.copy()
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    frame["month"] = frame["purchase_date"].dt.to_period("M").astype(str)
    monthly = (
        frame.groupby(["product", "month"], as_index=False)["unit_price"]
        .median()
        .rename(columns={"unit_price": "price"})
    )
    return monthly.sort_values("month")


def base_weights(history: pd.DataFrame) -> pd.Series:
    """Share of the basket by first-month spend, in percent.

    Fixed at the first month so later changes measure price movement rather
    than a change in what the household bought. Shared by the per-product
    change and the basket index so the two always agree.
    """
    if history.empty:
        return pd.Series(dtype=float)
    frame = history.copy()
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    frame["month"] = frame["purchase_date"].dt.to_period("M").astype(str)
    first_month = frame["month"].min()
    base = frame[frame["month"] == first_month]
    spend = (base["unit_price"].astype(float) * base["quantity"].astype(float)).groupby(
        base["product"]
    ).sum()
    total = spend.sum()
    if not total:
        return spend * 0
    return (spend / total * 100).fillna(0)


def personal_inflation(
    source, min_observations: int | None = None
) -> pd.DataFrame:
    """Per-product change from the first to the last observed month.

    ``source`` is a Session or an already-built history DataFrame, so the demo
    and the database path share one implementation.
    """
    min_observations = min_observations or settings.MIN_OBSERVATIONS
    history = source if isinstance(source, pd.DataFrame) else personal_price_history(source)
    columns = [
        "product", "category", "base_month", "latest_month", "base_price",
        "latest_price", "change_pct", "observations", "spend", "weight_pct",
    ]
    if history.empty:
        return pd.DataFrame(columns=columns)

    monthly = monthly_prices(history)
    weights = base_weights(history)
    meta = history.groupby("product").agg(
        category=("category", "last"),
        observations=("purchase_date", "nunique"),
        spend=("total_price", "sum"),
    )

    rows = []
    for product, frame in monthly.groupby("product"):
        frame = frame.sort_values("month")
        if len(frame) < min_observations:
            continue
        base_price = float(frame.iloc[0]["price"])
        latest_price = float(frame.iloc[-1]["price"])
        if base_price <= 0:
            continue
        rows.append({
            "product": product,
            "category": meta.loc[product, "category"] if product in meta.index else None,
            "base_month": frame.iloc[0]["month"],
            "latest_month": frame.iloc[-1]["month"],
            "base_price": round(base_price, 2),
            "latest_price": round(latest_price, 2),
            "change_pct": round((latest_price / base_price - 1) * 100, 2),
            "observations": int(meta.loc[product, "observations"]) if product in meta.index else len(frame),
            "spend": round(float(meta.loc[product, "spend"]), 2) if product in meta.index else 0.0,
            "weight_pct": round(float(weights.get(product, 0)), 1),
        })
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("change_pct", ascending=False)


def basket_change(inflation: pd.DataFrame) -> float | None:
    """Spend-weighted change across the whole basket."""
    if inflation.empty or inflation["weight_pct"].sum() <= 0:
        return None
    weights = inflation["weight_pct"] / inflation["weight_pct"].sum()
    return round(float((inflation["change_pct"] * weights).sum()), 2)


def basket_index(history: pd.DataFrame) -> pd.DataFrame:
    """A Laspeyres-style index of the user's own basket, rebased to 100.

    Fixed quantities from the first month, so the line answers "what would my
    usual basket cost now?" rather than "how did my shopping mix change?".
    """
    if history.empty:
        return pd.DataFrame(columns=["month", "index", "coverage"])
    monthly = monthly_prices(history)
    pivot = monthly.pivot_table(index="month", columns="product", values="price").sort_index()
    if pivot.empty:
        return pd.DataFrame(columns=["month", "index", "coverage"])
    pivot = pivot.ffill()
    base = pivot.iloc[0].dropna()
    if base.empty:
        return pd.DataFrame(columns=["month", "index", "coverage"])

    products = [product for product in base.index if product in base_weights(history).index]
    if not products:
        return pd.DataFrame(columns=["month", "index", "coverage"])
    weights = base_weights(history).reindex(products).fillna(0).astype(float)
    total_weight = float(weights.sum())
    if not total_weight:
        weights = base[products].astype(float)
        total_weight = float(weights.sum())
    prices = pivot[products].astype(float)
    base_prices = base[products].astype(float)
    relatives = prices.div(base_prices, axis=1)
    index = (relatives * weights).sum(axis=1) / total_weight * 100

    coverage = monthly.groupby("month")["product"].nunique().reindex(index.index).fillna(0)
    result = pd.DataFrame({
        "month": index.index,
        "index": index.round(2).values,
        "coverage": coverage.astype(int).values,
    })
    return result.reset_index(drop=True)


def category_breakdown(inflation: pd.DataFrame) -> pd.DataFrame:
    """Roll product changes up to categories, weighted by spend."""
    columns = ["category", "weight_pct", "change_pct", "products"]
    if inflation.empty:
        return pd.DataFrame(columns=columns)
    frame = inflation.copy()
    frame["category"] = frame["category"].fillna("Other")
    rows = []
    for category, group in frame.groupby("category"):
        weight = float(group["weight_pct"].sum())
        if weight <= 0:
            continue
        change = float((group["change_pct"] * group["weight_pct"]).sum() / weight)
        rows.append({
            "category": category,
            "weight_pct": round(weight, 1),
            "change_pct": round(change, 2),
            "products": int(len(group)),
        })
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("weight_pct", ascending=False)


def shrinkflation(history: pd.DataFrame, tolerance: float = 2.0) -> pd.DataFrame:
    """Products whose pack got smaller (or whose price per gram jumped).

    Compares the first and last observation that carries a pack size, and
    normalises everything to price per 100 g / 100 ml.
    """
    columns = [
        "product", "base_size", "latest_size", "size_change_pct", "base_price",
        "latest_price", "price_change_pct", "per_unit_base", "per_unit_latest",
        "per_unit_change_pct", "unit_label", "flagged",
    ]
    if history.empty:
        return pd.DataFrame(columns=columns)

    frame = history.dropna(subset=["package_size"]).copy()
    frame = frame[frame["package_size"] > 0]
    frame = frame[frame["package_unit"].isin(["g", "ml"])]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    frame = frame.sort_values("purchase_date")
    rows = []
    for product, group in frame.groupby("product"):
        if group["package_size"].nunique() < 1:
            continue
        first = group.iloc[0]
        last = group.iloc[-1]
        base_size = float(first["package_size"])
        latest_size = float(last["package_size"])
        base_price = float(first["unit_price"])
        latest_price = float(last["unit_price"])
        unit_label = "100 g" if first["package_unit"] == "g" else "100 ml"

        def per_unit(price: float, size: float) -> float:
            return round(price / size * 100, 2) if size else 0.0

        size_change = round((latest_size / base_size - 1) * 100, 1) if base_size else 0.0
        per_base = per_unit(base_price, base_size)
        per_latest = per_unit(latest_price, latest_size)
        per_change = round((per_latest / per_base - 1) * 100, 1) if per_base else 0.0
        flagged = size_change <= -tolerance or (
            per_change >= 10 and abs(size_change) >= tolerance
        )
        rows.append({
            "product": product,
            "base_size": base_size,
            "latest_size": latest_size,
            "size_change_pct": size_change,
            "base_price": round(base_price, 2),
            "latest_price": round(latest_price, 2),
            "price_change_pct": round((latest_price / base_price - 1) * 100, 1) if base_price else 0.0,
            "per_unit_base": per_base,
            "per_unit_latest": per_latest,
            "per_unit_change_pct": per_change,
            "unit_label": unit_label,
            "flagged": flagged,
        })
    result = pd.DataFrame(rows, columns=columns)
    return result.sort_values("per_unit_change_pct", ascending=False).reset_index(drop=True)


def store_spread(history: pd.DataFrame) -> pd.DataFrame:
    """Latest price of each product at each store, and the gap to the cheapest."""
    columns = ["product", "store_name", "latest_price", "last_seen", "vs_cheapest_pct"]
    if history.empty:
        return pd.DataFrame(columns=columns)
    frame = history.dropna(subset=["store_name"]).copy()
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    latest = (
        frame.sort_values("purchase_date")
        .groupby(["product", "store_name"], as_index=False)
        .agg(latest_price=("unit_price", "last"), last_seen=("purchase_date", "last"))
    )
    latest["cheapest"] = latest.groupby("product")["latest_price"].transform("min")
    latest["vs_cheapest_pct"] = (
        (latest["latest_price"] / latest["cheapest"] - 1) * 100
    ).round(1)
    latest = latest[latest.groupby("product")["store_name"].transform("nunique") > 1]
    return latest[columns].sort_values(["product", "latest_price"]).reset_index(drop=True)


def spend_by_month(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["month", "spend"])
    frame = history.copy()
    frame["purchase_date"] = pd.to_datetime(frame["purchase_date"])
    frame["month"] = frame["purchase_date"].dt.to_period("M").astype(str)
    monthly = frame.groupby("month", as_index=False)["total_price"].sum()
    return monthly.rename(columns={"total_price": "spend"}).sort_values("month")


# --------------------------------------------------------------------------- #
# Official CPI
# --------------------------------------------------------------------------- #

def cpi_history(session: Session, country: str = "IN") -> pd.DataFrame:
    rows = session.execute(
        select(CPIData.period, CPIData.category, CPIData.series_id, CPIData.index_value)
        .where(CPIData.country == country)
        .order_by(CPIData.period)
    ).all()
    if not rows:
        return pd.DataFrame(columns=["period", "category", "series_id", "index_value"])
    frame = pd.DataFrame(rows, columns=["period", "category", "series_id", "index_value"])
    frame["period"] = pd.to_datetime(frame["period"]).dt.to_period("M").astype(str)
    return frame


def cpi_rebased(
    cpi: pd.DataFrame, base_month: str | None = None, series: str | None = None
) -> pd.DataFrame:
    """Rebase an official series so the base month reads 100."""
    if cpi.empty:
        return pd.DataFrame(columns=["month", "index", "category"])
    frame = cpi.copy()
    if series and series in set(frame["series_id"]):
        frame = frame[frame["series_id"] == series]
    elif frame["series_id"].nunique() > 1:
        # Never average unrelated series together: use the most complete one.
        counts = frame.groupby("series_id")["period"].count()
        frame = frame[frame["series_id"] == counts.idxmax()]
    frame = frame.groupby("period", as_index=False)["index_value"].mean()
    frame = frame.sort_values("period")
    if base_month is None:
        base_month = str(frame.iloc[0]["period"])
    candidates = frame[frame["period"] == base_month]
    if candidates.empty:
        candidates = frame[frame["period"] >= base_month]
    if candidates.empty:
        return pd.DataFrame(columns=["month", "index", "category"])
    base_value = float(candidates.iloc[0]["index_value"])
    if base_value == 0:
        return pd.DataFrame(columns=["month", "index", "category"])
    frame = frame[frame["period"] >= base_month]
    return pd.DataFrame({
        "month": frame["period"].values,
        "index": (frame["index_value"] / base_value * 100).round(2).values,
        "category": "Official CPI",
    }).reset_index(drop=True)


def cpi_change(cpi: pd.DataFrame, base_month: str | None = None) -> float | None:
    rebased = cpi_rebased(cpi, base_month)
    if rebased.empty:
        return None
    return round(float(rebased.iloc[-1]["index"]) - 100, 1)


def cpi_series_options(cpi: pd.DataFrame) -> list[tuple[str, str]]:
    """(series_id, label) pairs for the picker."""
    if cpi.empty:
        return []
    options = (
        cpi.groupby(["series_id", "category"])["period"]
        .count()
        .reset_index()
        .sort_values("category")
    )
    return [(row["series_id"], f'{row["category"]} ({row["period"]} months)')
            for _, row in options.iterrows()]
