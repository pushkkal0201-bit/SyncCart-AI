from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    CartQuantityConflict,
    IdempotencyConflict,
    InvalidIdempotencyKey,
    ProductNotFound,
    SessionNotFound,
)
from app.models.cart import CartItem, CartSource
from app.models.event import DomainEvent, EventSource, EventType
from app.models.idempotency import IdempotencyRecord
from app.models.mixins import utcnow
from app.models.product import Product
from app.models.shopping_session import SessionStatus, ShoppingSession
from app.repositories.cart import CartRepository
from app.repositories.events import EventRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.products import ProductRepository
from app.repositories.sessions import SessionRepository
from app.schemas.cart import CartLineRead, CartRead
from app.schemas.reconciliation import PhysicalMutationResult
from app.services.reconciliation import ReconciliationService


class PhysicalCartService:
    def __init__(self) -> None:
        self.cart_repository = CartRepository()
        self.event_repository = EventRepository()
        self.idempotency_repository = IdempotencyRepository()
        self.product_repository = ProductRepository()
        self.session_repository = SessionRepository()
        self.reconciliation_service = ReconciliationService()
        self.settings = get_settings()

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _validate_idempotency_key(key: str | None) -> str | None:
        if key is None:
            return None
        normalized = key.strip()
        if not normalized or len(normalized) > 128:
            raise InvalidIdempotencyKey("Idempotency-Key must contain 1 to 128 characters")
        return normalized

    def _get_session(self, db: Session, session_id: str) -> ShoppingSession:
        shopping_session = self.session_repository.get(db, session_id)
        if shopping_session is None:
            raise SessionNotFound(f"Shopping session '{session_id}' was not found")
        if shopping_session.status == SessionStatus.COMPLETED.value:
            raise CartQuantityConflict("This shopping session is already completed")
        return shopping_session

    def _get_product(self, db: Session, sku: str) -> Product:
        product = self.product_repository.get_by_sku(db, sku.strip().upper())
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found")
        return product

    def _physical_cart(self, db: Session, *, session_id: str) -> CartRead:
        items = self.cart_repository.list_items(db, session_id=session_id, source=CartSource.PHYSICAL)
        lines: list[CartLineRead] = []
        totals_by_currency: dict[str, int] = {}
        total_quantity = 0
        for item in items:
            line_total = item.quantity * item.product.unit_price_minor
            totals_by_currency[item.product.currency] = totals_by_currency.get(item.product.currency, 0) + line_total
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
            source=CartSource.PHYSICAL.value,
            items=lines,
            distinct_items=len(lines),
            total_quantity=total_quantity,
            totals_by_currency=totals_by_currency,
        )

    def mutate(
        self,
        db: Session,
        *,
        session_id: str,
        sku: str,
        quantity: int,
        confidence: float,
        camera_id: str,
        zone_id: str,
        event_type: EventType,
        idempotency_key: str | None,
        simulated: bool = True,
        operation_prefix: str = "SIMULATOR",
        extra_payload: dict[str, object] | None = None,
    ) -> PhysicalMutationResult:
        shopping_session = self._get_session(db, session_id)
        product = self._get_product(db, sku)
        idempotency_key = self._validate_idempotency_key(idempotency_key)
        operation = f"{operation_prefix}_{event_type.value}"
        fingerprint = self._fingerprint(
            {
                "sku": product.sku,
                "quantity": quantity,
                "confidence": confidence,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "event_type": event_type.value,
                "simulated": simulated,
            }
        )
        if idempotency_key is not None:
            record = self.idempotency_repository.get(
                db,
                session_id=session_id,
                operation=operation,
                idempotency_key=idempotency_key,
            )
            if record is not None:
                if record.request_fingerprint != fingerprint:
                    raise IdempotencyConflict(
                        "This Idempotency-Key was already used with a different request payload"
                    )
                replay = PhysicalMutationResult.model_validate(record.response_payload)
                return replay.model_copy(update={"idempotent_replay": True})

        if confidence < self.settings.min_vision_confidence:
            reconciliation = self.reconciliation_service.get_status(db, session_id=session_id)
            return PhysicalMutationResult(
                operation=operation,
                accepted=False,
                reason="LOW_VISION_CONFIDENCE_REJECTED",
                event_id=None,
                sku=product.sku,
                quantity_delta=0,
                physical_cart=self._physical_cart(db, session_id=session_id),
                reconciliation=reconciliation,
            )

        item = self.cart_repository.get_item(
            db,
            session_id=session_id,
            product_id=product.id,
            source=CartSource.PHYSICAL,
        )
        if item is None:
            item = CartItem(
                session_id=session_id,
                product_id=product.id,
                source=CartSource.PHYSICAL.value,
                quantity=0,
                confidence=confidence,
            )
            self.cart_repository.add(db, item)

        delta = quantity if event_type == EventType.VISION_PICKUP else -quantity
        if item.quantity + delta < 0:
            raise CartQuantityConflict(
                f"Cannot return {quantity} unit(s); physical cart contains only {item.quantity}"
            )

        now = utcnow()
        item.quantity += delta
        item.confidence = confidence
        item.updated_at = now
        shopping_session.last_activity_at = now
        correlation_id = str(uuid4())
        event = self.event_repository.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=event_type.value,
                source=EventSource.VISION.value,
                sku=product.sku,
                quantity=quantity,
                confidence=confidence,
                correlation_id=correlation_id,
                camera_id=camera_id,
                zone_id=zone_id,
                payload={"simulated": simulated, **(extra_payload or {})},
            ),
        )
        db.flush()
        reconciliation = self.reconciliation_service.reconcile_session(
            db,
            session_id=session_id,
            trigger_event_id=event.id,
            now=now,
        )
        result = PhysicalMutationResult(
            operation=operation,
            accepted=True,
            reason=event_type.value,
            event_id=event.id,
            sku=product.sku,
            quantity_delta=delta,
            physical_cart=self._physical_cart(db, session_id=session_id),
            reconciliation=reconciliation,
        )
        if idempotency_key is not None:
            self.idempotency_repository.add(
                db,
                IdempotencyRecord(
                    session_id=session_id,
                    operation=operation,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    response_payload=result.model_dump(mode="json"),
                ),
            )
        db.commit()
        return result
