"""SQLAlchemy table definitions (schema from the project spec, plus audit columns)."""
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config.constants import CPISourceType, ProcessingStatus, VerificationStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_name: Mapped[str | None] = mapped_column(String(200))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    receipt_total: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    original_file_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 -> duplicate guard
    raw_ocr_text: Mapped[str | None] = mapped_column(Text)           # kept untouched for auditing
    processing_status: Mapped[str] = mapped_column(
        String(20), default=ProcessingStatus.UPLOADED.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_receipts_purchase_date", "purchase_date"),)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(50))
    package_size: Mapped[float | None] = mapped_column(Float)
    package_unit: Mapped[str | None] = mapped_column(String(20))

    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    # Different brand / size / unit => different product (spec requirement).
    # Note: SQLite treats NULLs as distinct in UNIQUE, so the repository layer
    # (Phase 4) must also check for duplicates before inserting.
    __table_args__ = (
        UniqueConstraint(
            "normalized_name", "brand", "package_size", "package_unit",
            name="uq_product_identity",
        ),
    )


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    alias_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"))
    alias_name: Mapped[str] = mapped_column(String(200), unique=True)

    product: Mapped["Product"] = relationship(back_populates="aliases")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    purchase_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.receipt_id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit: Mapped[str | None] = mapped_column(String(20))
    package_size: Mapped[float | None] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float | None] = mapped_column(Float)
    discount: Mapped[float] = mapped_column(Float, default=0)
    verification_status: Mapped[str] = mapped_column(
        String(10), default=VerificationStatus.PENDING.value
    )

    # Audit trail: what OCR originally read, kept separate from user corrections.
    ocr_line_text: Mapped[str | None] = mapped_column(Text)
    ocr_product_name: Mapped[str | None] = mapped_column(String(200))
    ocr_total_price: Mapped[float | None] = mapped_column(Float)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    user_corrected: Mapped[bool] = mapped_column(Boolean, default=False)

    receipt: Mapped["Receipt"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_items_receipt", "receipt_id"),
        Index("ix_items_product", "product_id"),
    )


class CPIData(Base):
    __tablename__ = "cpi_data"

    cpi_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(100))        # e.g. "BLS", "MoSPI"
    source_type: Mapped[str] = mapped_column(String(15), default=CPISourceType.API.value)
    series_id: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(100))
    period: Mapped[date] = mapped_column(Date)               # first day of the month
    index_value: Mapped[float] = mapped_column(Float)
    base_period: Mapped[str | None] = mapped_column(String(50))
    seasonally_adjusted: Mapped[bool | None] = mapped_column(Boolean)
    retrieval_date: Mapped[datetime] = mapped_column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("country", "series_id", "period", name="uq_cpi_observation"),
        Index("ix_cpi_lookup", "country", "series_id", "period"),
    )
