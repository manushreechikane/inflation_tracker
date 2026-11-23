"""Database repository helpers."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.data_management.models import (
    CPIData,
    Product,
    ProductAlias,
    PurchaseItem,
    Receipt,
)


def normalize_name(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def get_or_create_product(session: Session, name: str) -> Product:
    normalized = normalize_name(name)
    product = session.scalar(select(Product).where(Product.normalized_name == normalized))
    if product:
        return product
    product = Product(product_name=name.strip(), normalized_name=normalized)
    session.add(product)
    session.flush()
    alias = ProductAlias(alias_name=name.strip(), product_id=product.product_id)
    session.add(alias)
    return product


def find_receipt_by_hash(session: Session, file_hash: str) -> Receipt | None:
    return session.scalar(select(Receipt).where(Receipt.file_hash == file_hash))


def upsert_cpi(
    session: Session,
    *,
    country: str,
    source: str,
    source_type: str,
    series_id: str,
    category: str,
    period,
    index_value: float,
) -> CPIData:
    existing = session.scalar(
        select(CPIData).where(
            CPIData.country == country,
            CPIData.series_id == series_id,
            CPIData.period == period,
        )
    )
    if existing:
        existing.index_value = index_value
        existing.category = category
        return existing
    record = CPIData(
        country=country,
        source=source,
        source_type=source_type,
        series_id=series_id,
        category=category,
        period=period,
        index_value=index_value,
    )
    session.add(record)
    return record
