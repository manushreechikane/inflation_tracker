"""Sample receipts rendered on demand so the demo can be tried without a photo.

They are drawn, not scanned, which keeps them legible for Tesseract while still
exercising the same OCR -> parse -> verify path as a real upload.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
]


def _font(size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:  # pragma: no cover - corrupt font file
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - Pillow < 10.1
        return ImageFont.load_default()


SAMPLE_TEXTS: dict[str, dict] = {
    "monthly-shop": {
        "store": "More Supermarket",
        "date": "22/11/2026",
        "lines": [
            ("AASHIRVAAD ATTA 5 KG", "1,299.00"),
            ("TOOR DAL 1 KG", "178.00"),
            ("AMUL TONED MILK 500 ML", "34.00"),
            ("FORTUNE SUNFLOWER OIL 1 L", "139.00"),
            ("TATA SALT 1 KG", "29.00"),
            ("SURF EXCEL 1 KG", "142.00"),
            ("BRITANNIA BROWN BREAD 400 G", "60.00"),
        ],
        "subtotal": "1,881.00",
        "discount": ("BILL DISCOUNT", "31.00"),
        "total": "1,850.00",
    },
    "corner-kirana": {
        "store": "Shree Ganesh Kirana",
        "date": "19/11/2026",
        "lines": [
            ("AMUL TONED MILK 500 ML", "34.00"),
            ("2 X BRITANNIA BROWN BREAD 400 G", "120.00"),
            ("ONION 1 KG", "52.00"),
            ("TOMATO 1 KG", "34.00"),
            ("FARM EGGS 6 PCS", "54.00"),
        ],
        "subtotal": "294.00",
        "discount": None,
        "total": "294.00",
    },
}

SAMPLE_NAMES = {
    "monthly-shop": "Monthly shop — More Supermarket",
    "corner-kirana": "Top-up trip — Shree Ganesh Kirana",
}


def render_sample(name: str) -> bytes:
    """Draw a receipt PNG and return its bytes."""
    spec = SAMPLE_TEXTS[name]
    font = _font(24)
    small = _font(20)
    width = 620
    line_height = 38
    height = 200 + line_height * (len(spec["lines"]) + 6)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = 28

    def text_line(value: str, size_font=font, offset_x: int = 40):
        nonlocal y
        draw.text((offset_x, y), value, fill=(20, 20, 20), font=size_font)
        y += line_height

    def row(left: str, right: str):
        nonlocal y
        draw.text((40, y), left, fill=(20, 20, 20), font=small)
        right_width = draw.textlength(right, font=small)
        draw.text((width - 40 - right_width, y), right, fill=(20, 20, 20), font=small)
        y += line_height

    text_line(spec["store"])
    text_line(f"Date: {spec['date']}", small)
    y += 8
    for left, right in spec["lines"]:
        row(left, right)
    y += 4
    row("SUBTOTAL", spec["subtotal"])
    if spec["discount"]:
        row(*spec["discount"])
    row("TOTAL", spec["total"])
    y += 6
    text_line("Thank you, visit again", small)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
