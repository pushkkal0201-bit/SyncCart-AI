from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.cart import CartSource
from app.models.event import DomainEvent, EventSource, EventType
from app.models.mixins import utcnow
from app.models.reconciliation import DiscrepancyStatus, NudgeStatus
from app.models.shopping_session import SessionStatus
from app.repositories.cart import CartRepository
from app.repositories.events import EventRepository
from app.repositories.reconciliation import DiscrepancyRepository, NudgeRepository
from app.repositories.sessions import SessionRepository
from app.schemas.event import EventRead
from app.schemas.reconciliation import ReconciliationRead
from app.schemas.store_ops import (
    ReviewQueueItemRead,
    ReviewResolutionAction,
    ReviewResolutionResult,
    StoreMetricsRead,
    StoreOverviewRead,
    StoreSessionDetailRead,
    StoreSessionSummaryRead,
)
from app.services.reconciliation import ReconciliationService


class ReviewNotFound(DomainError):
    code = "REVIEW_NOT_FOUND"
    status_code = 404


class ReviewNotActionable(DomainError):
    code = "REVIEW_NOT_ACTIONABLE"
    status_code = 409


class StoreOperationsService:
    def __init__(self) -> None:
        self.sessions = SessionRepository()
        self.discrepancies = DiscrepancyRepository()
        self.nudges = NudgeRepository()
        self.events = EventRepository()
        self.cart = CartRepository()
        self.reconciliation = ReconciliationService()

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _session_summary(self, db: Session, session_id: str, *, now: datetime) -> StoreSessionSummaryRead:
        session = self.sessions.get(db, session_id)
        if session is None:
            raise ReviewNotFound(f"Session '{session_id}' was not found")
        state = self.reconciliation.get_status(db, session_id=session_id)
        duration = max(0, int((now - self._aware(session.started_at)).total_seconds()))
        primary_issue = None
        if state.active_discrepancies:
            issue = state.active_discrepancies[0]
            primary_issue = f"{issue.sku} {issue.difference:+d}"
        return StoreSessionSummaryRead(
            session_id=session.id,
            public_id=session.public_id,
            status=session.status,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            duration_seconds=duration,
            physical_quantity=state.cart.physical_cart.total_quantity,
            digital_quantity=state.cart.digital_cart.total_quantity,
            discrepancy_count=len(state.active_discrepancies),
            consistency_score=state.cart_consistency_score,
            primary_issue=primary_issue,
        )

    def list_sessions(self, db: Session, *, limit: int = 100) -> list[StoreSessionSummaryRead]:
        now = utcnow()
        sessions = self.sessions.list(db)[:limit]
        return [self._session_summary(db, item.id, now=now) for item in sessions]

    def review_queue(self, db: Session, *, limit: int = 100) -> list[ReviewQueueItemRead]:
        now = utcnow()
        rows = self.discrepancies.list_by_status(
            db,
            statuses=(DiscrepancyStatus.REVIEW_REQUIRED.value,),
            limit=limit,
        )
        output: list[ReviewQueueItemRead] = []
        for item in rows:
            session = self.sessions.get(db, item.session_id)
            if session is None:
                continue
            nudge = self.nudges.latest_for_discrepancy(db, discrepancy_id=item.id)
            waiting = max(0, int((now - self._aware(item.updated_at)).total_seconds()))
            output.append(
                ReviewQueueItemRead(
                    discrepancy_id=item.id,
                    session_id=item.session_id,
                    public_id=session.public_id,
                    sku=item.sku,
                    product_name=item.product.name,
                    status=item.status,
                    difference=item.difference,
                    physical_quantity=item.physical_quantity,
                    digital_quantity=item.digital_quantity,
                    risk_score=item.risk_score,
                    vision_confidence=item.vision_confidence,
                    reason_codes=list(item.reason_codes),
                    opened_at=item.opened_at,
                    updated_at=item.updated_at,
                    waiting_seconds=waiting,
                    nudge_status=nudge.status if nudge else None,
                    nudge_sent_at=nudge.sent_at if nudge else None,
                )
            )
        return output

    def overview(self, db: Session) -> StoreOverviewRead:
        now = utcnow()
        sessions = self.sessions.list(db)
        summaries = [self._session_summary(db, item.id, now=now) for item in sessions[:25]]
        status_counts = Counter(item.status for item in sessions)
        active_sessions = [
            item
            for item in sessions
            if item.status not in {SessionStatus.COMPLETED.value}
        ]
        active_discrepancies = self.discrepancies.list_by_status(
            db,
            statuses=self.discrepancies.ACTIVE_STATUSES,
            limit=500,
        )
        active_nudges = sum(
            1
            for item in active_discrepancies
            if (nudge := self.nudges.latest_for_discrepancy(db, discrepancy_id=item.id)) is not None
            and nudge.status in {NudgeStatus.SENT.value, NudgeStatus.ACKNOWLEDGED.value}
        )
        metrics = StoreMetricsRead(
            active_sessions=len(active_sessions),
            synced_sessions=sum(
                1
                for item in active_sessions
                if item.status in {
                    SessionStatus.CLEAR.value,
                    SessionStatus.RESOLVED.value,
                    SessionStatus.CHECKOUT_APPROVED.value,
                }
            ),
            verifying_sessions=sum(
                1
                for item in active_sessions
                if item.status in {SessionStatus.VERIFY.value, SessionStatus.NUDGE.value}
            ),
            review_required=sum(
                1
                for item in active_sessions
                if item.status in {SessionStatus.REVIEW.value, SessionStatus.CHECKOUT_BLOCKED.value}
            ),
            open_discrepancies=len(active_discrepancies),
            active_nudges=active_nudges,
            resolved_sessions=status_counts.get(SessionStatus.RESOLVED.value, 0),
        )
        return StoreOverviewRead(
            generated_at=now,
            metrics=metrics,
            status_counts=dict(status_counts),
            recent_sessions=summaries,
            review_queue=self.review_queue(db, limit=20),
        )

    def session_detail(self, db: Session, *, session_id: str) -> StoreSessionDetailRead:
        state = self.reconciliation.get_status(db, session_id=session_id)
        events = self.sessions.list_events(db, session_id)
        return StoreSessionDetailRead(
            reconciliation=state,
            events=[EventRead.model_validate(item) for item in events],
        )

    def resolve_review(
        self,
        db: Session,
        *,
        discrepancy_id: str,
        action: ReviewResolutionAction,
        note: str,
    ) -> ReviewResolutionResult:
        discrepancy = self.discrepancies.get(db, discrepancy_id)
        if discrepancy is None:
            raise ReviewNotFound(f"Discrepancy '{discrepancy_id}' was not found")
        if discrepancy.status != DiscrepancyStatus.REVIEW_REQUIRED.value:
            raise ReviewNotActionable("Only REVIEW_REQUIRED discrepancies can be resolved by store operations")

        now = utcnow()
        if action == ReviewResolutionAction.ESCALATE_MANUAL_CHECK:
            self.events.add(
                db,
                DomainEvent(
                    session_id=discrepancy.session_id,
                    event_type=EventType.SESSION_UPDATED.value,
                    source=EventSource.OPERATOR.value,
                    sku=discrepancy.sku,
                    quantity=abs(discrepancy.difference),
                    correlation_id=discrepancy.correlation_id,
                    payload={
                        "operator_action": action.value,
                        "discrepancy_id": discrepancy.id,
                        "note": note,
                    },
                ),
            )
            db.commit()
            return ReviewResolutionResult(
                discrepancy_id=discrepancy.id,
                action=action,
                resolved=False,
                message="Review remains open and has been escalated for manual verification.",
                reconciliation=self.reconciliation.get_status(db, session_id=discrepancy.session_id),
            )

        cart_item = self.cart.get_item(
            db,
            session_id=discrepancy.session_id,
            product_id=discrepancy.product_id,
            source=CartSource.PHYSICAL,
        )
        target_quantity = discrepancy.digital_quantity
        if cart_item is not None:
            cart_item.quantity = target_quantity
            cart_item.updated_at = now
            if target_quantity == 0:
                cart_item.confidence = None

        shopping_session = self.sessions.get(db, discrepancy.session_id)
        if shopping_session is not None:
            shopping_session.status = SessionStatus.RESOLVED.value
            shopping_session.last_activity_at = now

        discrepancy.status = DiscrepancyStatus.RESOLVED.value
        discrepancy.physical_quantity = target_quantity
        discrepancy.difference = 0
        discrepancy.risk_score = 0.0
        discrepancy.updated_at = now
        discrepancy.resolved_at = now
        discrepancy.reason_codes = [f"OPERATOR_{action.value}"]

        nudge = self.nudges.latest_for_discrepancy(db, discrepancy_id=discrepancy.id)
        if nudge is not None and nudge.status != NudgeStatus.RESOLVED.value:
            nudge.status = NudgeStatus.RESOLVED.value
            nudge.resolved_at = now
            nudge.action = action.value

        self.events.add(
            db,
            DomainEvent(
                session_id=discrepancy.session_id,
                event_type=EventType.REVIEW_RESOLVED.value,
                source=EventSource.OPERATOR.value,
                sku=discrepancy.sku,
                quantity=max(1, abs(discrepancy.physical_quantity - discrepancy.digital_quantity) or 1),
                correlation_id=discrepancy.correlation_id or str(uuid4()),
                payload={
                    "discrepancy_id": discrepancy.id,
                    "operator_action": action.value,
                    "note": note,
                    "physical_cart_corrected_to_digital_quantity": target_quantity,
                },
            ),
        )
        db.flush()
        state = self.reconciliation.reconcile_session(
            db,
            session_id=discrepancy.session_id,
            now=now,
        )
        db.commit()
        return ReviewResolutionResult(
            discrepancy_id=discrepancy.id,
            action=action,
            resolved=True,
            message=(
                "False detection confirmed; physical projection was corrected."
                if action == ReviewResolutionAction.FALSE_DETECTION
                else "Physical return confirmed by the colleague; cart projection was corrected."
            ),
            reconciliation=state,
        )
