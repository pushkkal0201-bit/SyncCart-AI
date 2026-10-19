from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reconciliation import Discrepancy, DiscrepancyStatus, EventMatch, Nudge


class DiscrepancyRepository:
    ACTIVE_STATUSES = (
        DiscrepancyStatus.VERIFYING.value,
        DiscrepancyStatus.NUDGE_SENT.value,
        DiscrepancyStatus.REVIEW_REQUIRED.value,
    )


    def get(self, db: Session, discrepancy_id: str) -> Discrepancy | None:
        return db.get(Discrepancy, discrepancy_id)

    def list_by_status(
        self,
        db: Session,
        *,
        statuses: tuple[str, ...],
        limit: int = 100,
    ) -> list[Discrepancy]:
        statement = (
            select(Discrepancy)
            .where(Discrepancy.status.in_(statuses))
            .order_by(Discrepancy.updated_at.desc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def add(self, db: Session, discrepancy: Discrepancy) -> Discrepancy:
        db.add(discrepancy)
        db.flush()
        return discrepancy

    def get_active_for_sku(
        self, db: Session, *, session_id: str, sku: str
    ) -> Discrepancy | None:
        statement = (
            select(Discrepancy)
            .where(
                Discrepancy.session_id == session_id,
                Discrepancy.sku == sku,
                Discrepancy.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(Discrepancy.opened_at.desc())
            .limit(1)
        )
        return db.scalar(statement)

    def list_for_session(self, db: Session, *, session_id: str) -> list[Discrepancy]:
        statement = (
            select(Discrepancy)
            .where(Discrepancy.session_id == session_id)
            .order_by(Discrepancy.opened_at.asc())
        )
        return list(db.scalars(statement).all())

    def list_active(self, db: Session, *, session_id: str) -> list[Discrepancy]:
        statement = (
            select(Discrepancy)
            .where(
                Discrepancy.session_id == session_id,
                Discrepancy.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(Discrepancy.opened_at.asc())
        )
        return list(db.scalars(statement).all())


class EventMatchRepository:
    def add(self, db: Session, event_match: EventMatch) -> EventMatch:
        db.add(event_match)
        db.flush()
        return event_match

    def event_is_matched(self, db: Session, event_id: str) -> bool:
        statement = select(EventMatch.id).where(
            (EventMatch.physical_event_id == event_id) | (EventMatch.digital_event_id == event_id)
        )
        return db.scalar(statement.limit(1)) is not None


class NudgeRepository:
    def get(self, db: Session, nudge_id: str) -> Nudge | None:
        return db.get(Nudge, nudge_id)

    def add(self, db: Session, nudge: Nudge) -> Nudge:
        db.add(nudge)
        db.flush()
        return nudge

    def latest_for_discrepancy(self, db: Session, *, discrepancy_id: str) -> Nudge | None:
        statement = (
            select(Nudge)
            .where(Nudge.discrepancy_id == discrepancy_id)
            .order_by(Nudge.sent_at.desc())
            .limit(1)
        )
        return db.scalar(statement)

    def list_for_session(self, db: Session, *, session_id: str, limit: int = 20) -> list[Nudge]:
        statement = (
            select(Nudge)
            .where(Nudge.session_id == session_id)
            .order_by(Nudge.sent_at.desc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())
