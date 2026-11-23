from datetime import date

from modules.receipt_processing.receipt_processor import parse_receipt


def test_parse_receipt_extracts_date_total_and_items():
    text = """Fresh Mart
2026-11-22
Milk 500g 65.00
Bread 40.50
TOTAL 105.50
"""
    parsed = parse_receipt(text)
    assert parsed["purchase_date"] == date(2026, 11, 22)
    assert parsed["receipt_total"] == 105.50
    assert {item["ocr_product_name"] for item in parsed["items"]} >= {"Milk 500g", "Bread"}
