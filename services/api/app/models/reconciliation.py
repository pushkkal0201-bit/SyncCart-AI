from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class DiscrepancyStatus(StrEnum):
    VERIFYING = "VERIFYING"
    NUDGE_SENT = "NUDGE_SENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class NudgeStatus(StrEnum):
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Discrepancy(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "discrepancies"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_discrepancy_risk_range"),
        CheckConstraint(
            "vision_confidence IS NULL OR (vision_confidence >= 0 AND vision_confidence <= 1)",
            name="ck_discrepancy_vision_confidence_range",
        ),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=DiscrepancyStatus.VERIFYING.value, nullable=False, index=True
    )
    physical_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    digital_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    difference: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    grace_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product = relationship("Product")


class EventMatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_matches"
    __table_args__ = (
        UniqueConstraint("physical_event_id", name="uq_event_match_physical"),
        UniqueConstraint("digital_event_id", name="uq_event_match_digital"),
        CheckConstraint(
            "match_confidence >= 0 AND match_confidence <= 1",
            name="ck_event_match_confidence_range",
        ),
        CheckConstraint("matched_quantity > 0", name="ck_event_match_quantity_positive"),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    physical_event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    digital_event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    matched_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Nudge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "nudges"

    discrepancy_id: Mapped[str] = mapped_column(
        ForeignKey("discrepancies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=NudgeStatus.SENT.value, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True)
