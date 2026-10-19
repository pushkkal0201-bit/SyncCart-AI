from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import NudgeNotFound, SessionNotFound
from app.models.event import DomainEvent, EventSource, EventType
from app.models.mixins import utcnow
from app.models.reconciliation import NudgeStatus
from app.models.shopping_session import SessionStatus
from app.repositories.events import EventRepository
from app.repositories.reconciliation import NudgeRepository
from app.repositories.sessions import SessionRepository
from app.schemas.customer_actions import (
    CheckoutResult,
    CustomerNudgeAction,
    NudgeActionResult,
)
from app.services.customer_auth import CustomerAuthService
from app.services.reconciliation import ReconciliationService


class CustomerActionService:
    def __init__(self) -> None:
        self.sessions = SessionRepository()
        self.events = EventRepository()
        self.nudges = NudgeRepository()
        self.auth = CustomerAuthService()
        self.reconciliation = ReconciliationService()

    def _authorize(self, db: Session, *, session_id: str, customer_token: str | None):
        shopping_session = self.sessions.get(db, session_id)
        if shopping_session is None:
            raise SessionNotFound(f"Shopping session '{session_id}' was not found")
        self.auth.verify(shopping_session, customer_token)
        return shopping_session

    def respond_to_nudge(
        self,
        db: Session,
        *,
        session_id: str,
        nudge_id: str,
        action: CustomerNudgeAction,
        customer_token: str | None,
    ) -> NudgeActionResult:
        shopping_session = self._authorize(
            db, session_id=session_id, customer_token=customer_token
        )
        nudge = self.nudges.get(db, nudge_id)
        if nudge is None or nudge.session_id != session_id:
            raise NudgeNotFound(f"Nudge '{nudge_id}' was not found for this session")

        now = utcnow()
        nudge.status = NudgeStatus.ACKNOWLEDGED.value
        nudge.acknowledged_at = now
        nudge.action = action.value

        if action == CustomerNudgeAction.I_RETURNED_IT:
            event_type = EventType.CUSTOMER_CONFIRMED_RETURN
            message = "Return noted. Place the item back on the shelf while SyncCart verifies it."
        elif action == CustomerNudgeAction.GET_HELP:
            event_type = EventType.CUSTOMER_REQUESTED_HELP
            shopping_session.status = SessionStatus.REVIEW.value
            message = "A store colleague has been requested to help with this item."
        else:
            event_type = EventType.NUDGE_ACKNOWLEDGED
            message = "Scanner ready. Scan the item to resynchronize your cart."

        self.events.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=event_type.value,
                source=EventSource.CUSTOMER.value,
                sku=nudge.sku,
                correlation_id=str(uuid4()),
                payload={"nudge_id": nudge.id, "action": action.value},
            ),
        )
        shopping_session.last_activity_at = now
        db.flush()
        state = self.reconciliation.get_status(db, session_id=session_id)
        db.commit()
        return NudgeActionResult(
            nudge_id=nudge.id,
            action=action,
            message=message,
            reconciliation=state,
        )

    def checkout(
        self,
        db: Session,
        *,
        session_id: str,
        customer_token: str | None,
    ) -> CheckoutResult:
        shopping_session = self._authorize(
            db, session_id=session_id, customer_token=customer_token
        )
        now = utcnow()
        shopping_session.checkout_requested_at = now
        self.events.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=EventType.CHECKOUT_REQUESTED.value,
                source=EventSource.CUSTOMER.value,
                correlation_id=str(uuid4()),
                payload={"payment_mode": "SIMULATED"},
            ),
        )
        db.flush()
        state = self.reconciliation.reconcile_session(db, session_id=session_id, now=now)
        approved = len(state.active_discrepancies) == 0

        if approved:
            shopping_session.status = SessionStatus.CHECKOUT_APPROVED.value
            event_type = EventType.CHECKOUT_APPROVED
            message = "Everything matches. You are clear to exit."
        else:
            shopping_session.status = SessionStatus.CHECKOUT_BLOCKED.value
            event_type = EventType.CHECKOUT_REJECTED
            message = "One or more items need targeted verification before exit."

        self.events.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=event_type.value,
                source=EventSource.SYSTEM.value,
                correlation_id=str(uuid4()),
                payload={
                    "payment_mode": "SIMULATED",
                    "active_discrepancies": len(state.active_discrepancies),
                },
            ),
        )
        shopping_session.last_activity_at = now
        db.commit()
        final_state = self.reconciliation.get_status(db, session_id=session_id)
        return CheckoutResult(
            approved=approved,
            payment_mode="SIMULATED",
            session_status=shopping_session.status,
            message=message,
            reconciliation=final_state,
        )
