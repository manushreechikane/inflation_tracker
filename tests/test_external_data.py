from datetime import date

import pandas as pd

from modules.external_data.cpi import (
    parse_bls_payload,
    parse_cpi_csv,
    sample_cpi_frame,
    sample_rows,
)


def test_parse_bls_payload_skips_annual_averages():
    payload = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [{
                "seriesID": "CUUR0000SA0",
                "data": [
                    {"year": "2026", "period": "M11", "value": "320.1"},
                    {"year": "2026", "period": "M10", "value": "319.4"},
                    {"year": "2026", "period": "M13", "value": "318.0"},
                    {"year": "2026", "period": "M12", "value": "bad"},
                ],
            }]
        },
    }
    rows = parse_bls_payload(payload)
    assert len(rows) == 2
    assert rows[0]["period"] == date(2026, 11, 1)
    assert rows[0]["category"] == "All items"
    assert rows[0]["series_id"] == "CUUR0000SA0"


def test_parse_cpi_csv_accepts_optional_columns():
    frame = pd.DataFrame({
        "Period": ["2026-01-01", "2026-02-01", "nonsense"],
        "Index_Value": ["101.5", "102.4", "x"],
        "Category": ["Food at home", "Food at home", "Food at home"],
    })
    rows = parse_cpi_csv(frame, "IN")
    assert len(rows) == 2
    assert rows[1]["period"] == date(2026, 2, 1)
    assert rows[1]["series_id"] == "MANUAL-IN"
    assert rows[1]["index_value"] == 102.4


def test_parse_cpi_csv_requires_the_two_core_columns():
    try:
        parse_cpi_csv(pd.DataFrame({"period": ["2026-01-01"]}), "IN")
    except ValueError as exc:
        assert "index_value" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected a ValueError")


def test_sample_series_is_labelled_and_monotonic():
    frame = sample_cpi_frame(date(2026, 11, 1), months=6)
    assert len(frame) == 6
    assert frame["category"].iloc[0].endswith("(sample)")
    assert frame["index_value"].is_monotonic_increasing
    rows = sample_rows()
    assert rows and all("illustrative" in row["source"].lower() for row in rows)
