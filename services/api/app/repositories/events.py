from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import DomainEvent


class EventRepository:
    def add(self, db: Session, event: DomainEvent) -> DomainEvent:
        db.add(event)
        db.flush()
        return event

    def get(self, db: Session, event_id: str) -> DomainEvent | None:
        return db.scalar(select(DomainEvent).where(DomainEvent.id == event_id))

    def latest_for_sku(
        self,
        db: Session,
        *,
        session_id: str,
        event_type: str,
        sku: str,
        created_after: datetime,
    ) -> DomainEvent | None:
        statement = (
            select(DomainEvent)
            .where(
                DomainEvent.session_id == session_id,
                DomainEvent.event_type == event_type,
                DomainEvent.sku == sku,
                DomainEvent.created_at >= created_after,
            )
            .order_by(DomainEvent.created_at.desc())
            .limit(1)
        )
        return db.scalar(statement)

    def candidates_for_match(
        self,
        db: Session,
        *,
        session_id: str,
        sku: str,
        event_types: tuple[str, ...],
        created_after: datetime,
        created_before: datetime,
    ) -> list[DomainEvent]:
        statement = (
            select(DomainEvent)
            .where(
                DomainEvent.session_id == session_id,
                DomainEvent.sku == sku,
                DomainEvent.event_type.in_(event_types),
                DomainEvent.created_at >= created_after,
                DomainEvent.created_at <= created_before,
            )
            .order_by(DomainEvent.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def latest_physical_for_sku(
        self,
        db: Session,
        *,
        session_id: str,
        sku: str,
    ) -> DomainEvent | None:
        statement = (
            select(DomainEvent)
            .where(
                DomainEvent.session_id == session_id,
                DomainEvent.sku == sku,
                DomainEvent.event_type.in_(("VISION_PICKUP", "VISION_RETURN")),
            )
            .order_by(DomainEvent.created_at.desc())
            .limit(1)
        )
        return db.scalar(statement)
