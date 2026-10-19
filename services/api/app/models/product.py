from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("unit_price_minor >= 0", name="ck_product_price_nonnegative"),)

    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit_price_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    expected_visual_class: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
