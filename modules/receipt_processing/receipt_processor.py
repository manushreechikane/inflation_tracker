"""Receipt file handling and OCR parsing."""
from __future__ import annotations

import hashlib
import re
from datetime import date
from io import BytesIO
from pathlib import Path

import pytesseract
from PIL import Image

from config import settings
from config.constants import ALLOWED_EXTENSIONS


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_upload(file_name: str, data: bytes) -> tuple[Path, str]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Supported formats: JPG, PNG, and PDF")

    file_hash = sha256_bytes(data)
    destination = settings.RECEIPTS_DIR / f"{file_hash}{suffix}"
    destination.write_bytes(data)
    return destination, file_hash


def extract_text(file_path: Path) -> str:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_path

            pages = convert_from_path(str(file_path), poppler_path=settings.POPPLER_PATH or None)
            return "\n".join(pytesseract.image_to_string(page) for page in pages)
        except Exception as exc:
            raise RuntimeError(f"Could not process PDF: {exc}") from exc

    return pytesseract.image_to_string(Image.open(file_path))


def extract_text_from_upload(file_name: str, data: bytes) -> str:
    """Run OCR on upload bytes without writing the receipt to server storage."""
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Supported formats: JPG, PNG, and PDF")
    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_bytes

            pages = convert_from_bytes(data, poppler_path=settings.POPPLER_PATH or None)
            return "\n".join(pytesseract.image_to_string(page) for page in pages)
        except Exception as exc:
            raise RuntimeError(f"Could not process PDF: {exc}") from exc

    with Image.open(BytesIO(data)) as image:
        return pytesseract.image_to_string(image)


def parse_receipt(raw_text: str) -> dict:
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines() if line.strip()]
    purchase_date = None
    for line in lines:
        match = re.search(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})", line)
        if match:
            value = match.group(1).replace("/", "-").replace(".", "-")
            parts = [int(p) for p in value.split("-")]
            try:
                if len(str(parts[0])) == 4:
                    purchase_date = date(parts[0], parts[1], parts[2])
                else:
                    purchase_date = date(parts[2], parts[1], parts[0])
            except ValueError:
                pass
            if purchase_date:
                break

    total = None
    total_lines = [l for l in lines if re.search(r"\b(total|grand|amount|net)\b", l, re.I)]
    for line in reversed(total_lines):
        match = re.findall(r"(?<!\d)(?:₹|rs\.?|[$])?\s*([0-9]+(?:[.,][0-9]{1,2})?)", line, re.I)
        if match:
            try:
                total = float(match[-1].replace(",", "."))
                break
            except ValueError:
                continue

    items = []
    price_pattern = re.compile(r"(?<!\d)(?:₹|rs\.?|[$])?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*$", re.I)
    for line in lines:
        if re.search(r"\b(total|subtotal|tax|change|cash|balance)\b", line, re.I):
            continue
        match = price_pattern.search(line)
        if not match:
            continue
        name = line[:match.start()].strip(" .-")
        name = re.sub(r"^\d+\s*[xX*@]\s*", "", name)
        if len(name) < 2:
            continue
        try:
            price = float(match.group(1).replace(",", "."))
        except ValueError:
            continue
        if price > 0:
            items.append({"ocr_product_name": name, "ocr_total_price": price, "ocr_line_text": line})

    return {
        "purchase_date": purchase_date or date.today(),
        "receipt_total": total,
        "store_name": lines[0][:200] if lines else None,
        "items": items,
    }
