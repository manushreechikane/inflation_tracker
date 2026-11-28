from datetime import date

from modules.receipt_processing.receipt_processor import (
    parse_date,
    parse_pack,
    parse_quantity,
    parse_receipt,
    to_float,
)


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


def test_thousand_separators_are_parsed_not_dropped():
    text = """More Supermarket
22/11/2026
AASHIRVAAD ATTA 5 KG 1,299.00
TOTAL 1,299.00
"""
    parsed = parse_receipt(text)
    assert [item["ocr_product_name"] for item in parsed["items"]] == ["AASHIRVAAD ATTA 5 KG"]
    assert parsed["items"][0]["ocr_total_price"] == 1299.0
    assert parsed["receipt_total"] == 1299.0


def test_to_float_handles_indian_grouping_and_decimal_comma():
    assert to_float("1,299.00") == 1299.0
    assert to_float("1,29,999.50") == 129999.5
    assert to_float("65,50") == 65.5
    assert to_float("42") == 42.0


def test_total_line_with_item_count_picks_the_amount_not_the_count():
    text = """Kirana
TOTAL 105.50 2 ITEMS
Milk 65.00
"""
    parsed = parse_receipt(text)
    assert parsed["receipt_total"] == 105.50


def test_quantity_prefix_is_extracted_into_unit_price():
    text = """Kirana
19/11/2026
2 X BRITANNIA BROWN BREAD 400 G 120.00
TOTAL 120.00
"""
    parsed = parse_receipt(text)
    item = parsed["items"][0]
    assert item["quantity"] == 2
    assert item["unit_price"] == 60.0
    assert item["package_size"] == 400
    assert item["package_unit"] == "g"


def test_discount_and_tax_lines_are_not_items():
    text = """Store
BILL DISCOUNT 31.00
CGST 5.00
Milk 34.00
TOTAL 39.00
"""
    parsed = parse_receipt(text)
    assert [item["ocr_product_name"] for item in parsed["items"]] == ["Milk"]


def test_line_item_gap_reports_a_missing_line():
    text = """Store
Milk 34.00
Bread 40.00
TOTAL 94.00
"""
    parsed = parse_receipt(text)
    assert parsed["items_total"] == 74.0
    assert parsed["line_item_gap"] == 20.0


def test_parse_pack_normalises_to_base_units():
    assert parse_pack("Atta 5 kg") == (5000.0, "g")
    assert parse_pack("Milk 500ml") == (500.0, "ml")
    assert parse_pack("Oil 1 L") == (1000.0, "ml")
    assert parse_pack("Eggs 6 pcs") == (6.0, "pcs")
    assert parse_pack("No pack here") == (None, None)


def test_parse_quantity_leading_and_trailing():
    assert parse_quantity("2 x Milk 500 ml") == (2.0, "Milk 500 ml")
    assert parse_quantity("Bread 3x") == (3.0, "Bread")
    assert parse_quantity("Rice 1 kg") == (1.0, "Rice 1 kg")


def test_parse_date_formats():
    assert parse_date("22/11/2026") == date(2026, 11, 22)
    assert parse_date("2026-11-22") == date(2026, 11, 22)
    assert parse_date("22 Nov 2026") == date(2026, 11, 22)
    assert parse_date("Nov 22, 2026") == date(2026, 11, 22)
    assert parse_date("22-11-26") == date(2026, 11, 22)
    assert parse_date("no date") is None


def test_category_is_guessed_from_the_name():
    parsed = parse_receipt("Store\nAMUL TONED MILK 500 ML 34.00\n")
    assert parsed["items"][0]["category"] == "Dairy"


def test_printed_discount_is_not_read_as_a_missing_line():
    from modules.receipt_processing.receipt_processor import OcrLine, parse_receipt_lines

    parsed = parse_receipt_lines([
        OcrLine("AASHIRVAAD ATTA 5 KG 1,299.00"),
        OcrLine("TOTAL 1,268.00"),
        OcrLine("BILL DISCOUNT 31.00"),
    ])
    assert parsed["discount_total"] == 31.0
    assert parsed["line_item_gap"] == 0
