"""Official CPI data: BLS API, CSV import and a bundled illustrative series.

Nothing here invents official statistics. The bundled series is generated from
a fixed annual rate, is clearly labelled "sample" everywhere it is shown, and
exists only so the demo has something to compare against.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from config import settings
from modules.data_management.repository import upsert_cpi

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# Public BLS series ids for the CPI-U, mapped to readable labels.
BLS_SERIES = {
    "CUUR0000SA0": "All items",
    "CUUR0000SAF1": "Food at home",
    "CUUR0000SAF11": "Cereals and bakery products",
    "CUUR0000SAF112": "Meats, poultry, fish and eggs",
    "CUUR0000SAF113": "Dairy and related products",
    "CUUR0000SAF114": "Fruits and vegetables",
    "CUUR0000SAF115": "Nonalcoholic beverages",
}

CPI_COLUMNS = ["period", "category", "series_id", "index_value"]


def parse_bls_payload(payload: dict) -> list[dict]:
    """Turn a BLS API response into CPI rows. Pure, so it is testable offline."""
    rows: list[dict] = []
    for series in payload.get("Results", {}).get("series", []) or []:
        series_id = series.get("seriesID", "")
        category = BLS_SERIES.get(series_id, series_id or "BLS series")
        for observation in series.get("data", []) or []:
            period_name = str(observation.get("period", ""))
            if not period_name.startswith("M") or period_name == "M13":
                continue
            try:
                month = int(period_name[1:])
                year = int(observation.get("year", 0))
                value = float(observation.get("value", ""))
            except (TypeError, ValueError):
                continue
            if not (1 <= month <= 12) or year <= 0:
                continue
            rows.append({
                "period": date(year, month, 1),
                "category": category,
                "series_id": series_id,
                "index_value": value,
                "source": "BLS",
            })
    return rows


def fetch_bls(
    series_ids: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Fetch CPI observations from the BLS public API v2."""
    import requests

    today = date.today()
    start_year = start_year or today.year - 2
    end_year = end_year or today.year
    payload = {
        "seriesid": series_ids or list(BLS_SERIES),
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    key = api_key if api_key is not None else settings.BLS_API_KEY
    if key:
        payload["registrationkey"] = key

    response = requests.post(BLS_URL, json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "REQUEST_SUCCEEDED":
        message = body.get("message") or body.get("status", "BLS request failed")
        raise RuntimeError(str(message))
    return parse_bls_payload(body)


def parse_cpi_csv(frame: pd.DataFrame, country: str) -> list[dict]:
    """Normalise an imported CSV into CPI rows.

    Required: ``period`` and ``index_value``. Optional: ``category``,
    ``series_id``, ``source``.
    """
    if frame is None or frame.empty:
        return []
    columns = {str(column).strip().lower(): column for column in frame.columns}
    if "period" not in columns or "index_value" not in columns:
        raise ValueError("CSV must contain period and index_value columns")

    series_id_default = f"MANUAL-{country}"
    rows: list[dict] = []
    for record in frame.to_dict("records"):
        period = pd.to_datetime(record.get(columns["period"]), errors="coerce")
        try:
            value = float(record.get(columns["index_value"]))
        except (TypeError, ValueError):
            continue
        if pd.isna(period) or value <= 0:
            continue
        category_column = columns.get("category")
        series_column = columns.get("series_id")
        source_column = columns.get("source")
        rows.append({
            "period": date(period.year, period.month, 1),
            "category": str(record.get(category_column) or "All items") if category_column else "All items",
            "series_id": str(record.get(series_column) or series_id_default) if series_column else series_id_default,
            "index_value": value,
            "source": str(record.get(source_column) or "Manual import") if source_column else "Manual import",
        })
    return rows


def store_rows(session, country: str, rows: list[dict], source_type: str = "manual_import") -> int:
    count = 0
    for row in rows:
        upsert_cpi(
            session,
            country=country,
            source=row.get("source", "Manual import"),
            source_type=source_type,
            series_id=row["series_id"],
            category=row["category"],
            period=row["period"],
            index_value=row["index_value"],
        )
        count += 1
    return count


# --------------------------------------------------------------------------- #
# Bundled illustrative series (demo only)
# --------------------------------------------------------------------------- #

SAMPLE_ANNUAL_RATE = 0.052
SAMPLE_MONTHS = 12


def sample_cpi_frame(
    end: date | None = None, months: int = SAMPLE_MONTHS, annual_rate: float = SAMPLE_ANNUAL_RATE
) -> pd.DataFrame:
    """A deterministic, clearly-labelled illustrative CPI series."""
    end = end or date.today()
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
    rows = []
    year, month = end.year, end.month
    periods: list[date] = []
    for _ in range(months):
        periods.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    periods.reverse()

    base_index = 187.4  # arbitrary starting level; only the shape is meaningful
    for index, period in enumerate(periods):
        rows.append({
            "period": period.strftime("%Y-%m"),
            "category": "Food at home (sample)",
            "series_id": "SAMPLE-FOOD",
            "index_value": round(base_index * (1 + monthly_rate) ** index, 2),
        })
    return pd.DataFrame(rows, columns=CPI_COLUMNS)


def sample_rows() -> list[dict]:
    return [
        {
            "period": date.fromisoformat(f"{row['period']}-01"),
            "category": row["category"],
            "series_id": row["series_id"],
            "index_value": row["index_value"],
            "source": "Bundled sample (illustrative)",
        }
        for row in sample_cpi_frame().to_dict("records")
    ]
