from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import SessionNotFound
from app.models.event import DomainEvent, EventSource, EventType
from app.models.shopping_session import ShoppingSession
from app.repositories.sessions import SessionRepository
from app.services.customer_auth import CustomerAuthService


class SessionService:
    def __init__(
        self,
        repository: SessionRepository | None = None,
        auth_service: CustomerAuthService | None = None,
    ) -> None:
        self.repository = repository or SessionRepository()
        self.auth_service = auth_service or CustomerAuthService()

    def create(self, db: Session) -> tuple[ShoppingSession, str]:
        token = uuid4().hex[:10].upper()
        customer_token, customer_token_hash, expires_at = self.auth_service.issue_token()
        shopping_session = ShoppingSession(
            public_id=f"SC-{token}",
            customer_token_hash=customer_token_hash,
            customer_token_expires_at=expires_at,
        )
        self.repository.add(db, shopping_session)
        event = DomainEvent(
            session_id=shopping_session.id,
            event_type=EventType.SESSION_STARTED.value,
            source=EventSource.SYSTEM.value,
            correlation_id=str(uuid4()),
            payload={"public_id": shopping_session.public_id},
        )
        db.add(event)
        db.commit()
        db.refresh(shopping_session)
        return shopping_session, customer_token

    def list(self, db: Session) -> list[ShoppingSession]:
        return self.repository.list(db)

    def get(self, db: Session, session_id: str) -> ShoppingSession:
        shopping_session = self.repository.get(db, session_id)
        if shopping_session is None:
            raise SessionNotFound(f"Shopping session '{session_id}' was not found")
        return shopping_session

    def events(self, db: Session, session_id: str) -> list[DomainEvent]:
        self.get(db, session_id)
        return self.repository.list_events(db, session_id)
