from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class EventType(StrEnum):
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_UPDATED = "SESSION_UPDATED"
    VISION_PICKUP = "VISION_PICKUP"
    VISION_RETURN = "VISION_RETURN"
    VISION_COUNT_CHANGED = "VISION_COUNT_CHANGED"
    PRODUCT_SCANNED = "PRODUCT_SCANNED"
    DIGITAL_ITEM_REMOVED = "DIGITAL_ITEM_REMOVED"
    MATCH_CONFIRMED = "MATCH_CONFIRMED"
    MATCH_EXPIRED = "MATCH_EXPIRED"
    DISCREPANCY_OPENED = "DISCREPANCY_OPENED"
    DISCREPANCY_UPDATED = "DISCREPANCY_UPDATED"
    DISCREPANCY_RESOLVED = "DISCREPANCY_RESOLVED"
    NUDGE_SENT = "NUDGE_SENT"
    NUDGE_ACKNOWLEDGED = "NUDGE_ACKNOWLEDGED"
    CUSTOMER_CONFIRMED_RETURN = "CUSTOMER_CONFIRMED_RETURN"
    CUSTOMER_REQUESTED_HELP = "CUSTOMER_REQUESTED_HELP"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEW_RESOLVED = "REVIEW_RESOLVED"
    CHECKOUT_REQUESTED = "CHECKOUT_REQUESTED"
    CHECKOUT_APPROVED = "CHECKOUT_APPROVED"
    CHECKOUT_REJECTED = "CHECKOUT_REJECTED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    CAMERA_CONNECTED = "CAMERA_CONNECTED"
    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    VISION_MODEL_LOADED = "VISION_MODEL_LOADED"
    VISION_MODEL_ERROR = "VISION_MODEL_ERROR"


class EventSource(StrEnum):
    API = "API"
    CUSTOMER = "CUSTOMER"
    VISION = "VISION"
    SYSTEM = "SYSTEM"
    OPERATOR = "OPERATOR"


class DomainEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_event_quantity_positive"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_event_confidence_range",
        ),
    )

    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    session = relationship("ShoppingSession", back_populates="events")
