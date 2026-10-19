from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import DomainEvent
from app.models.shopping_session import SessionStatus, ShoppingSession


class SessionRepository:
    def list(self, db: Session) -> list[ShoppingSession]:
        return list(db.scalars(select(ShoppingSession).order_by(ShoppingSession.started_at.desc())).all())

    def list_reconcilable(self, db: Session) -> list[ShoppingSession]:
        statement = select(ShoppingSession).where(
            ShoppingSession.status.notin_(
                (SessionStatus.COMPLETED.value, SessionStatus.CHECKOUT_APPROVED.value)
            )
        )
        return list(db.scalars(statement).all())

    def get(self, db: Session, session_id: str) -> ShoppingSession | None:
        return db.scalar(select(ShoppingSession).where(ShoppingSession.id == session_id))

    def add(self, db: Session, session: ShoppingSession) -> ShoppingSession:
        db.add(session)
        db.flush()
        return session

    def list_events(self, db: Session, session_id: str) -> list[DomainEvent]:
        statement = (
            select(DomainEvent)
            .where(DomainEvent.session_id == session_id)
            .order_by(DomainEvent.created_at.asc())
        )
        return list(db.scalars(statement).all())
