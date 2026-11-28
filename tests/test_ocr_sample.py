"""End-to-end OCR check against the rendered sample receipts.

Skipped automatically where Tesseract is not installed (the CI workflow
installs it, so this runs there).
"""
import shutil

import pytest

from modules.receipt_processing.receipt_processor import (
    ocr_lines_from_bytes,
    parse_receipt_lines,
)
from modules.receipt_processing.sample_receipts import SAMPLE_TEXTS, render_sample

requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None and not shutil.which("tesseract.exe"),
    reason="Tesseract is not installed",
)


def test_sample_receipt_renders_to_png():
    blob = render_sample("monthly-shop")
    assert blob.startswith(b"\x89PNG")
    assert len(blob) > 5000


@requires_tesseract
@pytest.mark.parametrize("name", list(SAMPLE_TEXTS))
def test_sample_receipt_survives_the_ocr_round_trip(name):
    parsed = parse_receipt_lines(ocr_lines_from_bytes(f"{name}.png", render_sample(name)))
    assert parsed["store_name"]
    assert parsed["purchase_date"] is not None
    assert len(parsed["items"]) >= 3
    assert parsed["receipt_total"] is not None


@requires_tesseract
def test_thousand_separator_survives_ocr():
    parsed = parse_receipt_lines(
        ocr_lines_from_bytes("monthly-shop.png", render_sample("monthly-shop"))
    )
    assert parsed["receipt_total"] == 1850.0
    assert any(item["ocr_total_price"] == 1299.0 for item in parsed["items"])
