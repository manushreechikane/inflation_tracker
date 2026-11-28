"""Receipt file handling, OCR and parsing.

Parsing is heuristic on purpose: there is no universal receipt format. Every
step degrades gracefully and returns what it could read, so the UI can always
show the user something to correct.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pytesseract
from PIL import Image

from config import settings
from config.constants import (
    ALLOWED_EXTENSIONS,
    CATEGORY_KEYWORDS,
    COUNT_UNITS,
    MASS_UNITS,
    RECEIPT_KEYWORDS,
    VOLUME_UNITS,
)

try:  # OpenCV improves OCR a lot but must never be a hard requirement.
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - exercised only when cv2 is absent
    cv2 = None
    np = None


# --------------------------------------------------------------------------- #
# OCR
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class OcrLine:
    """One visual line of text with Tesseract's mean word confidence."""

    text: str
    confidence: float | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _configure_tesseract() -> None:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def _preprocess(image: Image.Image) -> Image.Image:
    """Greyscale, upscale small photos and binarise. Falls back to greyscale."""
    grey = image.convert("L")
    if cv2 is None or np is None:
        return grey
    array = np.array(grey)
    if max(array.shape) < 1200:
        array = cv2.resize(array, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    array = cv2.bilateralFilter(array, 5, 50, 50)
    array = cv2.adaptiveThreshold(
        array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12
    )
    return Image.fromarray(array)


def _lines_from_image(image: Image.Image) -> list[OcrLine]:
    """Group Tesseract word boxes back into lines, keeping confidence."""
    _configure_tesseract()
    data = pytesseract.image_to_data(
        _preprocess(image), output_type=pytesseract.Output.DICT
    )
    grouped: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    for index, word in enumerate(data.get("text", [])):
        word = (word or "").strip()
        if not word:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0
        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        grouped.setdefault(key, []).append((word, confidence))

    lines: list[OcrLine] = []
    for key in sorted(grouped):
        words = grouped[key]
        text = re.sub(r"\s+", " ", " ".join(word for word, _ in words)).strip()
        if not text:
            continue
        scores = [score for _, score in words if score > 0]
        lines.append(OcrLine(text, round(sum(scores) / len(scores), 1) if scores else None))
    return lines


def ocr_lines_from_bytes(file_name: str, data: bytes) -> list[OcrLine]:
    """OCR an upload without writing it to disk (used by the public demo)."""
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Supported formats: JPG, PNG, and PDF")
    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_bytes

            pages = convert_from_bytes(
                data, poppler_path=settings.POPPLER_PATH or None, dpi=220
            )
        except Exception as exc:  # pragma: no cover - depends on Poppler
            raise RuntimeError(f"Could not open PDF: {exc}") from exc
        lines: list[OcrLine] = []
        for page in pages:
            lines.extend(_lines_from_image(page))
        return lines

    with Image.open(BytesIO(data)) as image:
        image.load()
        return _lines_from_image(image)


def ocr_lines_from_path(path: Path) -> list[OcrLine]:
    return ocr_lines_from_bytes(path.name, path.read_bytes())


def extract_text(file_path: Path) -> str:
    """Backwards-compatible: plain text for a file on disk."""
    return "\n".join(line.text for line in ocr_lines_from_path(file_path))


def extract_text_from_upload(file_name: str, data: bytes) -> str:
    """Backwards-compatible: plain text for an upload held in memory."""
    return "\n".join(line.text for line in ocr_lines_from_bytes(file_name, data))


def save_upload(file_name: str, data: bytes) -> tuple[Path, str]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Supported formats: JPG, PNG, and PDF")

    file_hash = sha256_bytes(data)
    destination = settings.RECEIPTS_DIR / f"{file_hash}{suffix}"
    destination.write_bytes(data)
    return destination, file_hash


# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #

# A number token that may carry Indian or Western thousands separators.
_NUMBER = re.compile(r"(?<![\d.,])(\d[\d,]*(?:\.\d{1,2})?)(?![\d.,])")
# Same, but the number has to be the last thing on the line: that is how
# receipts print a line's amount.
_END_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr|\$)?\s*(\d[\d,]*(?:\.\d{1,2})?)\s*"
    r"(?:₹|rs\.?|inr|\$|/-)?\s*[)*#]?\s*$",
    re.I,
)

_CURRENCY_RE = re.compile(r"(₹|rs\.?|inr|\$)", re.I)


def to_float(token: str) -> float | None:
    """Parse '1,299.00', '1,29,999', '65,50' and '65.00' into a float."""
    cleaned = token.strip().replace(" ", "").replace("₹", "").replace("$", "")
    cleaned = re.sub(r"(?i)(rs\.?|inr)", "", cleaned)
    if not cleaned:
        return None

    if "," in cleaned:
        whole, _, fraction = cleaned.partition(".")
        groups = whole.split(",")
        if len(groups) >= 3:
            # 1,29,999.50 -> Indian grouping, commas are thousands separators
            cleaned = "".join(groups) + (f".{fraction}" if fraction else "")
        elif len(groups) == 2 and len(groups[1]) == 3 and 1 <= len(groups[0]) <= 3:
            # 1,299.00 -> Western thousands separator
            cleaned = "".join(groups) + (f".{fraction}" if fraction else "")
        elif len(groups) == 2 and 1 <= len(groups[1]) <= 2:
            # 65,50 -> decimal comma
            cleaned = f"{groups[0]}.{groups[1]}"
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def amounts(line: str) -> list[float]:
    values = []
    for match in _NUMBER.finditer(line):
        value = to_float(match.group(1))
        if value is not None:
            values.append(value)
    return values


def end_amount(line: str) -> float | None:
    match = _END_AMOUNT.search(line)
    if not match:
        return None
    return to_float(match.group(1))


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        candidate = date(year, month, day)
    except ValueError:
        return None
    if not (2000 <= candidate.year <= 2100):
        return None
    return candidate


def parse_date(text: str) -> date | None:
    """Day-first by default (Indian receipts); also handles ISO and month names."""
    # 2026-11-22 / 2026/11/22
    match = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if match:
        found = _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if found:
            return found
    # 22/11/2026 or 22-11-26
    match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b", text)
    if match:
        day, month, year = (int(part) for part in match.groups())
        year = year + 2000 if year < 100 else year
        found = _safe_date(year, month, day) or _safe_date(year, day, month)
        if found:
            return found
    # 22 Nov 2026 / Nov 22, 2026
    match = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(20\d{2})\b", text)
    if match:
        month = _MONTHS.get(match.group(2).lower())
        if month:
            found = _safe_date(int(match.group(3)), month, int(match.group(1)))
            if found:
                return found
    match = re.search(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(20\d{2})\b", text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            found = _safe_date(int(match.group(3)), month, int(match.group(2)))
            if found:
                return found
    return None


# --------------------------------------------------------------------------- #
# Product names, quantities and pack sizes
# --------------------------------------------------------------------------- #

_PACK = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|kilogram|kilo|gm|gms|gram|grams|g|ml|millilitre|"
    r"milliliter|cc|ltr|litres|liters|litre|liter|lt|l|pcs|pc|pieces|piece|nos|"
    r"pack|pkt|packet|dozen)\b",
    re.I,
)

_LEADING_QTY = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:x|\*|@|nos\.?)\s+", re.I)
_QTY_AT_END = re.compile(r"\s+(\d+)\s*(?:x|\*)\s*$", re.I)


def parse_pack(name: str) -> tuple[float | None, str | None]:
    """Return (size, base_unit) normalised to grams / millilitres / count."""
    matches = list(_PACK.finditer(name))
    if not matches:
        return None, None
    match = matches[-1]
    size = float(match.group(1))
    unit = match.group(2).lower()
    if unit in MASS_UNITS:
        return round(size * MASS_UNITS[unit], 3), "g"
    if unit in VOLUME_UNITS:
        return round(size * VOLUME_UNITS[unit], 3), "ml"
    if unit in COUNT_UNITS:
        return round(size * COUNT_UNITS[unit], 3), "pcs"
    return None, None


def parse_quantity(name: str) -> tuple[float, str]:
    """Pull a leading or trailing multiplier out of a product name."""
    match = _LEADING_QTY.match(name)
    if match:
        return float(match.group(1)), name[match.end():].strip()
    match = _QTY_AT_END.search(name)
    if match:
        return float(match.group(1)), name[: match.start()].strip()
    return 1.0, name


def clean_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name).strip(" .-*:|\t")
    # Trailing unit price left over from "Milk 2 @ 65.00" style lines.
    cleaned = re.sub(r"\s+\d+(?:[.,]\d+)?\s*@\s*$", "", cleaned)
    cleaned = re.sub(r"\s+\d+(?:[.,]\d{1,2})\s*$", "", cleaned)
    return cleaned.strip(" .-*:|\t")


def guess_category(name: str) -> str:
    lowered = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Other"


def _looks_like_metadata(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in RECEIPT_KEYWORDS)


# --------------------------------------------------------------------------- #
# Receipt parsing
# --------------------------------------------------------------------------- #

def _parse_total(lines: list[OcrLine]) -> float | None:
    def is_total(text: str) -> bool:
        lowered = text.lower()
        if "subtotal" in lowered or "sub total" in lowered:
            return False
        return bool(
            re.search(r"\b(grand\s*total|total|amount\s*(payable|due)|net\s*amount|bill\s*amount)\b", lowered)
        )

    candidates = [line.text for line in lines if is_total(line.text)]
    for text in reversed(candidates):
        values = [value for value in amounts(text) if value > 0]
        if values:
            # "TOTAL 105.50 2 ITEMS" -> the total is the largest number on the line.
            return round(max(values), 2)
    return None


def parse_receipt_lines(lines: list[OcrLine]) -> dict:
    """Parse structured fields out of OCR lines."""
    clean_lines = [line for line in lines if line.text.strip()]
    texts = [line.text for line in clean_lines]

    purchase_date = None
    for text in texts[:15]:
        found = parse_date(text)
        if found:
            purchase_date = found
            break

    store_name = None
    for text in texts[:4]:
        letters = sum(character.isalpha() for character in text)
        if letters >= 3 and not _looks_like_metadata(text) and len(text) <= 80:
            store_name = text.strip()
            break

    items = []
    for line in clean_lines:
        text = line.text
        if _looks_like_metadata(text):
            continue
        match = _END_AMOUNT.search(text)
        if not match:
            continue
        amount = to_float(match.group(1))
        if amount is None or amount <= 0 or amount > 1_000_000:
            continue

        raw_name = text[: match.start()].strip()
        quantity, raw_name = parse_quantity(raw_name)
        name = clean_name(raw_name)
        if len(name) < 2 or sum(character.isalpha() for character in name) < 2:
            continue

        package_size, package_unit = parse_pack(name)
        if quantity <= 0:
            quantity = 1.0
        unit_price = round(amount / quantity, 2) if quantity else amount
        items.append({
            "ocr_product_name": name,
            "ocr_total_price": round(amount, 2),
            "quantity": quantity,
            "unit_price": unit_price,
            "package_size": package_size,
            "package_unit": package_unit,
            "category": guess_category(name),
            "ocr_line_text": text,
            "ocr_confidence": line.confidence,
        })

    receipt_total = _parse_total(clean_lines)
    items_total = round(sum(item["ocr_total_price"] for item in items), 2)

    confidence_values = [
        item["ocr_confidence"] for item in items if item["ocr_confidence"] is not None
    ]
    return {
        "purchase_date": purchase_date,
        "receipt_total": receipt_total,
        "store_name": store_name,
        "items": items,
        "items_total": items_total,
        "line_item_gap": (
            round(receipt_total - items_total, 2) if receipt_total is not None else None
        ),
        "ocr_confidence": (
            round(sum(confidence_values) / len(confidence_values), 1)
            if confidence_values else None
        ),
        "raw_text": "\n".join(texts),
    }


def parse_receipt(raw_text: str) -> dict:
    """Parse plain OCR text (no confidence available)."""
    lines = [OcrLine(line, None) for line in raw_text.splitlines() if line.strip()]
    return parse_receipt_lines(lines)


def uncertain_items(parsed: dict, threshold: float = 65.0) -> list[dict]:
    """Item rows Tesseract was not confident about."""
    return [
        item for item in parsed.get("items", [])
        if item.get("ocr_confidence") is not None and item["ocr_confidence"] < threshold
    ]


def receipt_date_or_today(parsed: dict) -> date:
    return parsed.get("purchase_date") or date.today()


def same_day(value) -> date:  # pragma: no cover - tiny helper for callers
    if isinstance(value, datetime):
        return value.date()
    return value
