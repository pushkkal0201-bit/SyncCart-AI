from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, utcnow


class IdempotencyRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_session_operation_key",
        ),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation: Mapped[str] = mapped_column(String(48), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
