from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import SessionNotFound
from app.models.cart import CartSource
from app.models.event import DomainEvent, EventSource, EventType
from app.models.mixins import utcnow
from app.models.reconciliation import (
    Discrepancy,
    DiscrepancyStatus,
    EventMatch,
    Nudge,
    NudgeStatus,
)
from app.models.shopping_session import SessionStatus, ShoppingSession
from app.repositories.cart import CartRepository
from app.repositories.events import EventRepository
from app.repositories.products import ProductRepository
from app.repositories.reconciliation import (
    DiscrepancyRepository,
    EventMatchRepository,
    NudgeRepository,
)
from app.repositories.sessions import SessionRepository
from app.schemas.cart import CartComparisonRead, CartLineRead, CartRead
from app.schemas.reconciliation import DiscrepancyRead, NudgeRead, ReconciliationRead


class ReconciliationService:
    def __init__(
        self,
        *,
        cart_repository: CartRepository | None = None,
        event_repository: EventRepository | None = None,
        product_repository: ProductRepository | None = None,
        discrepancy_repository: DiscrepancyRepository | None = None,
        event_match_repository: EventMatchRepository | None = None,
        nudge_repository: NudgeRepository | None = None,
        session_repository: SessionRepository | None = None,
    ) -> None:
        self.cart_repository = cart_repository or CartRepository()
        self.event_repository = event_repository or EventRepository()
        self.product_repository = product_repository or ProductRepository()
        self.discrepancy_repository = discrepancy_repository or DiscrepancyRepository()
        self.event_match_repository = event_match_repository or EventMatchRepository()
        self.nudge_repository = nudge_repository or NudgeRepository()
        self.session_repository = session_repository or SessionRepository()
        self.settings = get_settings()

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _get_session(self, db: Session, session_id: str) -> ShoppingSession:
        shopping_session = self.session_repository.get(db, session_id)
        if shopping_session is None:
            raise SessionNotFound(f"Shopping session '{session_id}' was not found")
        return shopping_session

    def _cart_read(self, db: Session, *, session_id: str, source: CartSource) -> CartRead:
        items = self.cart_repository.list_items(db, session_id=session_id, source=source)
        lines: list[CartLineRead] = []
        totals_by_currency: dict[str, int] = {}
        total_quantity = 0
        for item in items:
            line_total = item.quantity * item.product.unit_price_minor
            totals_by_currency[item.product.currency] = (
                totals_by_currency.get(item.product.currency, 0) + line_total
            )
            total_quantity += item.quantity
            lines.append(
                CartLineRead(
                    product_id=item.product.id,
                    sku=item.product.sku,
                    barcode=item.product.barcode,
                    name=item.product.name,
                    quantity=item.quantity,
                    unit_price_minor=item.product.unit_price_minor,
                    line_total_minor=line_total,
                    currency=item.product.currency,
                    confidence=item.confidence,
                    updated_at=item.updated_at,
                )
            )
        return CartRead(
            source=source.value,
            items=lines,
            distinct_items=len(lines),
            total_quantity=total_quantity,
            totals_by_currency=totals_by_currency,
        )

    @staticmethod
    def _quantities(cart: CartRead) -> dict[str, int]:
        return {item.sku: item.quantity for item in cart.items}

    def _try_match_trigger_event(
        self,
        db: Session,
        *,
        trigger_event_id: str | None,
        now: datetime,
    ) -> None:
        if trigger_event_id is None:
            return
        trigger = self.event_repository.get(db, trigger_event_id)
        if trigger is None or trigger.session_id is None or trigger.sku is None or trigger.quantity is None:
            return
        if self.event_match_repository.event_is_matched(db, trigger.id):
            return

        mapping: dict[str, tuple[tuple[str, ...], bool]] = {
            EventType.VISION_PICKUP.value: ((EventType.PRODUCT_SCANNED.value,), True),
            EventType.VISION_RETURN.value: ((EventType.DIGITAL_ITEM_REMOVED.value,), True),
            EventType.PRODUCT_SCANNED.value: ((EventType.VISION_PICKUP.value,), False),
            EventType.DIGITAL_ITEM_REMOVED.value: ((EventType.VISION_RETURN.value,), False),
        }
        pair = mapping.get(trigger.event_type)
        if pair is None:
            return
        opposite_types, trigger_is_physical = pair
        trigger_time = self._aware(trigger.created_at)
        window_start = trigger_time - timedelta(milliseconds=self.settings.event_match_window_ms)
        candidates = self.event_repository.candidates_for_match(
            db,
            session_id=trigger.session_id,
            sku=trigger.sku,
            event_types=opposite_types,
            created_after=window_start,
            created_before=trigger_time,
        )
        candidate = next(
            (
                event
                for event in candidates
                if event.quantity == trigger.quantity
                and not self.event_match_repository.event_is_matched(db, event.id)
            ),
            None,
        )
        if candidate is None:
            return

        physical = trigger if trigger_is_physical else candidate
        digital = candidate if trigger_is_physical else trigger
        physical_time = self._aware(physical.created_at)
        digital_time = self._aware(digital.created_at)
        delta_ms = abs((digital_time - physical_time).total_seconds() * 1000.0)
        temporal_factor = max(0.0, 1.0 - delta_ms / max(self.settings.event_match_window_ms, 1))
        vision_confidence = physical.confidence if physical.confidence is not None else 0.5
        match_confidence = round(min(1.0, 0.65 * vision_confidence + 0.35 * temporal_factor), 4)

        match = self.event_match_repository.add(
            db,
            EventMatch(
                session_id=trigger.session_id,
                sku=trigger.sku,
                physical_event_id=physical.id,
                digital_event_id=digital.id,
                matched_quantity=trigger.quantity,
                match_confidence=match_confidence,
                matched_at=now,
                metadata_json={"temporal_delta_ms": round(delta_ms, 2)},
            ),
        )
        self.event_repository.add(
            db,
            DomainEvent(
                session_id=trigger.session_id,
                event_type=EventType.MATCH_CONFIRMED.value,
                source=EventSource.SYSTEM.value,
                sku=trigger.sku,
                quantity=trigger.quantity,
                confidence=match.match_confidence,
                correlation_id=trigger.correlation_id,
                causation_id=trigger.id,
                payload={
                    "physical_event_id": physical.id,
                    "digital_event_id": digital.id,
                    "temporal_delta_ms": round(delta_ms, 2),
                    "match_confidence": match_confidence,
                },
            ),
        )

    def _risk_score(
        self,
        *,
        difference: int,
        elapsed_ms: float,
        vision_confidence: float | None,
        existing_status: str | None,
    ) -> float:
        quantity_factor = min(abs(difference) / 3.0, 1.0)
        time_factor = min(elapsed_ms / max(self.settings.scan_grace_period_ms, 1), 1.0)
        confidence_factor = vision_confidence if vision_confidence is not None else 0.5
        repeat_factor = 1.0 if existing_status in {
            DiscrepancyStatus.NUDGE_SENT.value,
            DiscrepancyStatus.REVIEW_REQUIRED.value,
        } else 0.0
        risk = (
            0.35 * quantity_factor
            + 0.25 * time_factor
            + 0.25 * confidence_factor
            + 0.15 * repeat_factor
        )
        return round(max(0.0, min(1.0, risk)), 4)

    def _reason_codes(self, difference: int) -> list[str]:
        if difference > 0:
            return ["PHYSICAL_AHEAD_OF_DIGITAL", "UNMATCHED_PHYSICAL_QUANTITY"]
        return ["DIGITAL_AHEAD_OF_PHYSICAL", "UNCONFIRMED_DIGITAL_QUANTITY"]

    def _open_discrepancy(
        self,
        db: Session,
        *,
        shopping_session: ShoppingSession,
        sku: str,
        physical_quantity: int,
        digital_quantity: int,
        difference: int,
        now: datetime,
    ) -> Discrepancy:
        product = self.product_repository.get_by_sku(db, sku)
        if product is None:
            raise RuntimeError(f"Cart references unknown SKU '{sku}'")
        latest_physical = self.event_repository.latest_physical_for_sku(
            db, session_id=shopping_session.id, sku=sku
        )
        vision_confidence = latest_physical.confidence if latest_physical is not None else None
        correlation_id = (
            latest_physical.correlation_id if latest_physical is not None else str(uuid4())
        )
        discrepancy = Discrepancy(
            session_id=shopping_session.id,
            product_id=product.id,
            sku=sku,
            status=DiscrepancyStatus.VERIFYING.value,
            physical_quantity=physical_quantity,
            digital_quantity=digital_quantity,
            difference=difference,
            risk_score=self._risk_score(
                difference=difference,
                elapsed_ms=0,
                vision_confidence=vision_confidence,
                existing_status=None,
            ),
            vision_confidence=vision_confidence,
            reason_codes=self._reason_codes(difference),
            correlation_id=correlation_id,
            opened_at=now,
            updated_at=now,
            grace_expires_at=now + timedelta(milliseconds=self.settings.scan_grace_period_ms),
        )
        self.discrepancy_repository.add(db, discrepancy)
        self.event_repository.add(
            db,
            DomainEvent(
                session_id=shopping_session.id,
                event_type=EventType.DISCREPANCY_OPENED.value,
                source=EventSource.SYSTEM.value,
                sku=sku,
                quantity=abs(difference),
                confidence=vision_confidence,
                correlation_id=correlation_id,
                payload={
                    "physical_quantity": physical_quantity,
                    "digital_quantity": digital_quantity,
                    "difference": difference,
                    "grace_expires_at": discrepancy.grace_expires_at.isoformat(),
                    "reason_codes": discrepancy.reason_codes,
                },
            ),
        )
        return discrepancy

    def _resolve_discrepancy(
        self,
        db: Session,
        *,
        discrepancy: Discrepancy,
        now: datetime,
        trigger_event_id: str | None,
    ) -> None:
        discrepancy.status = DiscrepancyStatus.RESOLVED.value
        discrepancy.physical_quantity = discrepancy.digital_quantity
        discrepancy.difference = 0
        discrepancy.risk_score = 0.0
        discrepancy.updated_at = now
        discrepancy.resolved_at = now
        discrepancy.reason_codes = ["CART_REALIGNED"]

        nudge = self.nudge_repository.latest_for_discrepancy(db, discrepancy_id=discrepancy.id)
        if nudge is not None and nudge.status != NudgeStatus.RESOLVED.value:
            nudge.status = NudgeStatus.RESOLVED.value
            nudge.resolved_at = now
            nudge.action = "CART_REALIGNED"

        self.event_repository.add(
            db,
            DomainEvent(
                session_id=discrepancy.session_id,
                event_type=EventType.DISCREPANCY_RESOLVED.value,
                source=EventSource.SYSTEM.value,
                sku=discrepancy.sku,
                quantity=1,
                correlation_id=discrepancy.correlation_id,
                causation_id=trigger_event_id,
                payload={"discrepancy_id": discrepancy.id, "resolution": "CART_REALIGNED"},
            ),
        )

    def _advance_discrepancy(
        self,
        db: Session,
        *,
        discrepancy: Discrepancy,
        now: datetime,
    ) -> None:
        elapsed_ms = max(
            0.0,
            (now - self._aware(discrepancy.opened_at)).total_seconds() * 1000.0,
        )
        discrepancy.risk_score = self._risk_score(
            difference=discrepancy.difference,
            elapsed_ms=elapsed_ms,
            vision_confidence=discrepancy.vision_confidence,
            existing_status=discrepancy.status,
        )
        discrepancy.updated_at = now

        if discrepancy.status == DiscrepancyStatus.VERIFYING.value and now >= self._aware(
            discrepancy.grace_expires_at
        ):
            self.event_repository.add(
                db,
                DomainEvent(
                    session_id=discrepancy.session_id,
                    event_type=EventType.MATCH_EXPIRED.value,
                    source=EventSource.SYSTEM.value,
                    sku=discrepancy.sku,
                    quantity=abs(discrepancy.difference),
                    correlation_id=discrepancy.correlation_id,
                    payload={"discrepancy_id": discrepancy.id},
                ),
            )
            if discrepancy.difference > 0:
                discrepancy.status = DiscrepancyStatus.NUDGE_SENT.value
                nudge = self.nudge_repository.add(
                    db,
                    Nudge(
                        discrepancy_id=discrepancy.id,
                        session_id=discrepancy.session_id,
                        sku=discrepancy.sku,
                        message=f"Did you forget to scan {discrepancy.product.name}?",
                        status=NudgeStatus.SENT.value,
                        sent_at=now,
                    ),
                )
                self.event_repository.add(
                    db,
                    DomainEvent(
                        session_id=discrepancy.session_id,
                        event_type=EventType.NUDGE_SENT.value,
                        source=EventSource.SYSTEM.value,
                        sku=discrepancy.sku,
                        quantity=abs(discrepancy.difference),
                        correlation_id=discrepancy.correlation_id,
                        payload={
                            "discrepancy_id": discrepancy.id,
                            "nudge_id": nudge.id,
                            "message": nudge.message,
                        },
                    ),
                )
            else:
                discrepancy.status = DiscrepancyStatus.REVIEW_REQUIRED.value
                self.event_repository.add(
                    db,
                    DomainEvent(
                        session_id=discrepancy.session_id,
                        event_type=EventType.REVIEW_REQUIRED.value,
                        source=EventSource.SYSTEM.value,
                        sku=discrepancy.sku,
                        quantity=abs(discrepancy.difference),
                        correlation_id=discrepancy.correlation_id,
                        payload={
                            "discrepancy_id": discrepancy.id,
                            "reason": "DIGITAL_AHEAD_OF_PHYSICAL",
                        },
                    ),
                )
            return

        if discrepancy.status == DiscrepancyStatus.NUDGE_SENT.value:
            nudge = self.nudge_repository.latest_for_discrepancy(
                db, discrepancy_id=discrepancy.id
            )
            if nudge is not None:
                review_at = self._aware(nudge.sent_at) + timedelta(
                    milliseconds=self.settings.nudge_to_review_ms
                )
                if now >= review_at:
                    discrepancy.status = DiscrepancyStatus.REVIEW_REQUIRED.value
                    self.event_repository.add(
                        db,
                        DomainEvent(
                            session_id=discrepancy.session_id,
                            event_type=EventType.REVIEW_REQUIRED.value,
                            source=EventSource.SYSTEM.value,
                            sku=discrepancy.sku,
                            quantity=abs(discrepancy.difference),
                            correlation_id=discrepancy.correlation_id,
                            payload={
                                "discrepancy_id": discrepancy.id,
                                "reason": "NUDGE_UNRESOLVED",
                            },
                        ),
                    )

    def reconcile_session(
        self,
        db: Session,
        *,
        session_id: str,
        trigger_event_id: str | None = None,
        now: datetime | None = None,
    ) -> ReconciliationRead:
        now = self._aware(now or utcnow())
        shopping_session = self._get_session(db, session_id)
        self._try_match_trigger_event(db, trigger_event_id=trigger_event_id, now=now)

        digital_cart = self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL)
        physical_cart = self._cart_read(db, session_id=session_id, source=CartSource.PHYSICAL)
        digital_qty = self._quantities(digital_cart)
        physical_qty = self._quantities(physical_cart)
        existing_active = self.discrepancy_repository.list_active(db, session_id=session_id)
        skus = sorted(
            set(digital_qty)
            | set(physical_qty)
            | {item.sku for item in existing_active}
        )
        resolved_this_cycle = False

        for sku in skus:
            p_qty = physical_qty.get(sku, 0)
            d_qty = digital_qty.get(sku, 0)
            difference = p_qty - d_qty
            active = self.discrepancy_repository.get_active_for_sku(
                db, session_id=session_id, sku=sku
            )
            if difference == 0:
                if active is not None:
                    active.digital_quantity = d_qty
                    self._resolve_discrepancy(
                        db,
                        discrepancy=active,
                        now=now,
                        trigger_event_id=trigger_event_id,
                    )
                    resolved_this_cycle = True
                continue

            if active is None:
                active = self._open_discrepancy(
                    db,
                    shopping_session=shopping_session,
                    sku=sku,
                    physical_quantity=p_qty,
                    digital_quantity=d_qty,
                    difference=difference,
                    now=now,
                )
            else:
                active.physical_quantity = p_qty
                active.digital_quantity = d_qty
                active.difference = difference
                active.reason_codes = self._reason_codes(difference)
                active.updated_at = now

            self._advance_discrepancy(db, discrepancy=active, now=now)

        active_discrepancies = self.discrepancy_repository.list_active(
            db, session_id=session_id
        )
        if active_discrepancies:
            statuses = {item.status for item in active_discrepancies}
            if DiscrepancyStatus.REVIEW_REQUIRED.value in statuses:
                shopping_session.status = SessionStatus.REVIEW.value
            elif DiscrepancyStatus.NUDGE_SENT.value in statuses:
                shopping_session.status = SessionStatus.NUDGE.value
            else:
                shopping_session.status = SessionStatus.VERIFY.value
        elif resolved_this_cycle:
            shopping_session.status = SessionStatus.RESOLVED.value
        elif skus:
            shopping_session.status = SessionStatus.CLEAR.value

        shopping_session.last_activity_at = now
        db.flush()
        return self.get_status(db, session_id=session_id)

    def get_status(self, db: Session, *, session_id: str) -> ReconciliationRead:
        shopping_session = self._get_session(db, session_id)
        digital_cart = self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL)
        physical_cart = self._cart_read(db, session_id=session_id, source=CartSource.PHYSICAL)
        active = self.discrepancy_repository.list_active(db, session_id=session_id)
        nudges = self.nudge_repository.list_for_session(db, session_id=session_id, limit=10)
        max_risk = max((item.risk_score for item in active), default=0.0)
        consistency_score = round((1.0 - max_risk) * 100.0, 2)
        reasons: list[str] = []
        for item in active:
            reasons.append(
                f"{item.sku}: physical={item.physical_quantity}, digital={item.digital_quantity}, "
                f"difference={item.difference}, status={item.status}"
            )
            if item.vision_confidence is not None:
                reasons.append(f"{item.sku}: vision confidence={item.vision_confidence:.2f}")
        if not reasons:
            reasons.append("Physical and digital cart projections are currently aligned.")

        cart = CartComparisonRead(
            session_id=shopping_session.id,
            public_id=shopping_session.public_id,
            session_status=shopping_session.status,
            digital_cart=digital_cart,
            physical_cart=physical_cart,
        )
        return ReconciliationRead(
            session_id=shopping_session.id,
            public_id=shopping_session.public_id,
            session_status=shopping_session.status,
            cart_consistency_score=consistency_score,
            active_discrepancies=[DiscrepancyRead.model_validate(item) for item in active],
            latest_nudges=[NudgeRead.model_validate(item) for item in nudges],
            reasons=reasons,
            cart=cart,
        )

    def list_discrepancies(self, db: Session, *, session_id: str) -> list[Discrepancy]:
        self._get_session(db, session_id)
        return self.discrepancy_repository.list_for_session(db, session_id=session_id)

    def sweep_session(
        self,
        db: Session,
        *,
        session_id: str,
        now: datetime | None = None,
    ) -> ReconciliationRead:
        return self.reconcile_session(db, session_id=session_id, now=now)

    def sweep_all(self, db: Session, *, now: datetime | None = None) -> int:
        sessions = self.session_repository.list_reconcilable(db)
        for shopping_session in sessions:
            self.reconcile_session(db, session_id=shopping_session.id, now=now)
        db.commit()
        return len(sessions)
