"""Database repository helpers: product identity, aliases, CPI upserts."""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:200]


def find_alias(session: Session, name: str) -> ProductAlias | None:
    key = _clean(name).lower()
    if not key:
        return None
    return session.scalar(
        select(ProductAlias).where(func.lower(ProductAlias.alias_name) == key)
    )


def _find_by_identity(
    session: Session,
    normalized: str,
    brand: str | None,
    package_size: float | None,
    package_unit: str | None,
) -> Product | None:
    query = select(Product).where(Product.normalized_name == normalized)
    query = query.where(
        Product.brand.is_(None) if brand is None else Product.brand == brand
    )
    query = query.where(
        Product.package_size.is_(None) if package_size is None
        else Product.package_size == package_size
    )
    query = query.where(
        Product.package_unit.is_(None) if package_unit is None
        else Product.package_unit == package_unit
    )
    return session.scalar(query.limit(1))


def learn_alias(session: Session, alias_name: str, product: Product) -> None:
    """Remember that this printed spelling means this product.

    Uses a savepoint so a duplicate alias can never take the receipt
    transaction down with it.
    """
    alias_name = _clean(alias_name)
    if not alias_name or find_alias(session, alias_name):
        return
    try:
        with session.begin_nested():
            session.add(ProductAlias(alias_name=alias_name, product_id=product.product_id))
    except IntegrityError:  # pragma: no cover - race with another writer
        return


def get_or_create_product(
    session: Session,
    name: str,
    *,
    brand: str | None = None,
    package_size: float | None = None,
    package_unit: str | None = None,
    category: str | None = None,
) -> Product:
    """Resolve a printed product name to one product row.

    Identity is (normalised name, brand, pack size, pack unit) so that
    "Milk 500 ml" and "Milk 1 L" stay separate products. A previously learned
    alias wins, which is what makes correcting a name stick.
    """
    clean = _clean(name)
    if not clean:
        raise ValueError("Product name is empty")

    alias = find_alias(session, clean)
    if alias:
        product = alias.product
        # An alias only applies when the pack/brand we were told about matches:
        # the same words over a different pack size are a different product.
        same_pack = (
            package_size is None
            or product.package_size is None
            or float(product.package_size) == float(package_size)
        )
        same_unit = (
            package_unit is None
            or product.package_unit is None
            or product.package_unit == package_unit
        )
        same_brand = brand is None or product.brand is None or product.brand == brand
        if same_pack and same_unit and same_brand:
            if category and not product.category:
                product.category = category
            return product

    normalized = normalize_name(clean)
    brand = _clean(brand) or None
    product = _find_by_identity(session, normalized, brand, package_size, package_unit)
    if product is None:
        product = Product(
            product_name=clean,
            normalized_name=normalized,
            brand=brand,
            package_size=package_size,
            package_unit=package_unit,
            category=category,
        )
        session.add(product)
        session.flush()
    elif category and not product.category:
        product.category = category

    learn_alias(session, clean, product)
    return product


def rename_product(session: Session, product: Product, new_name: str) -> Product:
    """Rename a product and remember the old spelling as an alias."""
    new_name = _clean(new_name)
    if not new_name:
        raise ValueError("New name is empty")
    new_normalized = normalize_name(new_name)
    if new_normalized == product.normalized_name:
        product.product_name = new_name
        return product

    clash = session.scalar(
        select(Product).where(
            Product.normalized_name == new_normalized,
            Product.product_id != product.product_id,
        )
    )
    if clash:
        raise ValueError(f"'{clash.product_name}' already uses that name")

    learn_alias(session, product.product_name, product)
    product.product_name = new_name
    product.normalized_name = new_normalized
    return product


def set_product_category(session: Session, product: Product, category: str | None) -> None:
    product.category = category


def find_receipt_by_hash(session: Session, file_hash: str) -> Receipt | None:
    return session.scalar(select(Receipt).where(Receipt.file_hash == file_hash))


def delete_receipt(session: Session, receipt_id: int) -> bool:
    receipt = session.get(Receipt, receipt_id)
    if receipt is None:
        return False
    session.delete(receipt)  # cascade removes purchase items
    return True


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
    base_period: str | None = None,
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
        existing.source = source
        existing.source_type = source_type
        if base_period:
            existing.base_period = base_period
        return existing
    record = CPIData(
        country=country,
        source=source,
        source_type=source_type,
        series_id=series_id,
        category=category,
        period=period,
        index_value=index_value,
        base_period=base_period,
    )
    session.add(record)
    return record


def receipt_item_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(PurchaseItem)) or 0
