from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.shopping_session import SessionStatus
from app.repositories.sessions import SessionRepository
from app.schemas.vision import VisionActiveSessionRead


class VisionGatewayService:
    """Resolves the controlled-zone camera-to-session association.

    Phase 5 intentionally supports one active shopper session in the observed shelf zone.
    If there is not exactly one eligible session, the Vision worker must not guess who owns
    a pickup. Ambiguous multi-session attribution is blocked at the watched-zone boundary rather than guessed.
    """

    def __init__(self) -> None:
        self.sessions = SessionRepository()

    def active_session(self, db: Session) -> VisionActiveSessionRead:
        eligible = [
            session
            for session in self.sessions.list_reconcilable(db)
            if session.status not in {
                SessionStatus.COMPLETED.value,
                SessionStatus.CHECKOUT_APPROVED.value,
            }
        ]
        if not eligible:
            return VisionActiveSessionRead(
                available=False,
                reason="NO_ACTIVE_SESSION",
            )
        if len(eligible) > 1:
            return VisionActiveSessionRead(
                available=False,
                reason="MULTIPLE_ACTIVE_SESSIONS_UNSUPPORTED_IN_WATCHED_ZONE",
            )
        session = eligible[0]
        return VisionActiveSessionRead(
            available=True,
            reason="SINGLE_ACTIVE_SESSION",
            session_id=session.id,
            public_id=session.public_id,
            status=session.status,
        )
