from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class CartSource(StrEnum):
    PHYSICAL = "PHYSICAL"
    DIGITAL = "DIGITAL"


class CartItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_cart_quantity_nonnegative"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_cart_confidence_range",
        ),
        UniqueConstraint("session_id", "product_id", "source", name="uq_cart_projection"),
    )

    session_id: Mapped[str] = mapped_column(ForeignKey("shopping_sessions.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    session = relationship("ShoppingSession", back_populates="cart_items")
    product = relationship("Product")
