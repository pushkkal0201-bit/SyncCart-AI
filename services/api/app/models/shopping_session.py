from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class SessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLEAR = "CLEAR"
    VERIFY = "VERIFY"
    NUDGE = "NUDGE"
    REVIEW = "REVIEW"
    RESOLVED = "RESOLVED"
    CHECKOUT_BLOCKED = "CHECKOUT_BLOCKED"
    CHECKOUT_APPROVED = "CHECKOUT_APPROVED"
    COMPLETED = "COMPLETED"


class ShoppingSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shopping_sessions"

    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=SessionStatus.ACTIVE.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    checkout_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cart_items = relationship("CartItem", back_populates="session", cascade="all, delete-orphan")
    events = relationship("DomainEvent", back_populates="session", cascade="all, delete-orphan")
