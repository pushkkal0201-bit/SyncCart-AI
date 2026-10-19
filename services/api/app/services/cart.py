from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    CartItemNotFound,
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
from app.schemas.cart import CartComparisonRead, CartLineRead, CartMutationResult, CartRead
from app.services.customer_auth import CustomerAuthService
from app.services.reconciliation import ReconciliationService


class CartService:
    def __init__(
        self,
        *,
        cart_repository: CartRepository | None = None,
        event_repository: EventRepository | None = None,
        idempotency_repository: IdempotencyRepository | None = None,
        product_repository: ProductRepository | None = None,
        session_repository: SessionRepository | None = None,
        auth_service: CustomerAuthService | None = None,
        reconciliation_service: ReconciliationService | None = None,
    ) -> None:
        self.cart_repository = cart_repository or CartRepository()
        self.event_repository = event_repository or EventRepository()
        self.idempotency_repository = idempotency_repository or IdempotencyRepository()
        self.product_repository = product_repository or ProductRepository()
        self.session_repository = session_repository or SessionRepository()
        self.auth_service = auth_service or CustomerAuthService()
        self.reconciliation_service = reconciliation_service or ReconciliationService()
        self.settings = get_settings()

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _fingerprint(payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _validate_idempotency_key(self, key: str | None) -> str | None:
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
        return shopping_session

    def _authorize_customer(
        self,
        db: Session,
        *,
        session_id: str,
        customer_token: str | None,
    ) -> ShoppingSession:
        shopping_session = self._get_session(db, session_id)
        self.auth_service.verify(shopping_session, customer_token)
        if shopping_session.status == SessionStatus.COMPLETED.value:
            raise CartQuantityConflict("This shopping session is already completed")
        return shopping_session

    def _get_product_by_barcode(self, db: Session, barcode: str) -> Product:
        product = self.product_repository.get_by_barcode(db, barcode.strip().upper())
        if product is None:
            raise ProductNotFound(f"No product is registered for barcode '{barcode}'")
        return product

    def _get_product_by_sku(self, db: Session, sku: str) -> Product:
        product = self.product_repository.get_by_sku(db, sku.strip().upper())
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found")
        return product

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

    def get_comparison(
        self,
        db: Session,
        *,
        session_id: str,
        customer_token: str | None,
    ) -> CartComparisonRead:
        shopping_session = self._authorize_customer(
            db,
            session_id=session_id,
            customer_token=customer_token,
        )
        return CartComparisonRead(
            session_id=shopping_session.id,
            public_id=shopping_session.public_id,
            session_status=shopping_session.status,
            digital_cart=self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL),
            physical_cart=self._cart_read(db, session_id=session_id, source=CartSource.PHYSICAL),
        )

    def _restore_idempotent_result(
        self,
        db: Session,
        *,
        session_id: str,
        operation: str,
        idempotency_key: str | None,
        request_fingerprint: str,
    ) -> CartMutationResult | None:
        if idempotency_key is None:
            return None
        record = self.idempotency_repository.get(
            db,
            session_id=session_id,
            operation=operation,
            idempotency_key=idempotency_key,
        )
        if record is None:
            return None
        if record.request_fingerprint != request_fingerprint:
            raise IdempotencyConflict(
                "This Idempotency-Key was already used with a different request payload"
            )
        result = CartMutationResult.model_validate(record.response_payload)
        return result.model_copy(update={"idempotent_replay": True})

    def _save_idempotent_result(
        self,
        db: Session,
        *,
        session_id: str,
        operation: str,
        idempotency_key: str | None,
        request_fingerprint: str,
        result: CartMutationResult,
    ) -> None:
        if idempotency_key is None:
            return
        self.idempotency_repository.add(
            db,
            IdempotencyRecord(
                session_id=session_id,
                operation=operation,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response_payload=result.model_dump(mode="json"),
            ),
        )

    def scan(
        self,
        db: Session,
        *,
        session_id: str,
        barcode: str,
        quantity: int,
        customer_token: str | None,
        idempotency_key: str | None,
    ) -> CartMutationResult:
        shopping_session = self._authorize_customer(
            db,
            session_id=session_id,
            customer_token=customer_token,
        )
        product = self._get_product_by_barcode(db, barcode)
        idempotency_key = self._validate_idempotency_key(idempotency_key)
        request_fingerprint = self._fingerprint(
            {"barcode": product.barcode, "quantity": quantity}
        )
        operation = "DIGITAL_SCAN"

        replay = self._restore_idempotent_result(
            db,
            session_id=session_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if replay is not None:
            return replay

        now = utcnow()
        duplicate_after = now - timedelta(milliseconds=self.settings.duplicate_scan_window_ms)
        latest_scan = self.event_repository.latest_for_sku(
            db,
            session_id=session_id,
            event_type=EventType.PRODUCT_SCANNED.value,
            sku=product.sku,
            created_after=duplicate_after,
        )
        if latest_scan is not None:
            digital_cart = self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL)
            result = CartMutationResult(
                operation=operation,
                accepted=False,
                reason="DUPLICATE_SCAN_SUPPRESSED",
                event_id=None,
                sku=product.sku,
                quantity_delta=0,
                digital_cart=digital_cart,
            )
            self._save_idempotent_result(
                db,
                session_id=session_id,
                operation=operation,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                result=result,
            )
            db.commit()
            return result

        cart_item = self.cart_repository.get_item(
            db,
            session_id=session_id,
            product_id=product.id,
            source=CartSource.DIGITAL,
        )
        if cart_item is None:
            cart_item = CartItem(
                session_id=session_id,
                product_id=product.id,
                source=CartSource.DIGITAL.value,
                quantity=0,
                confidence=None,
            )
            self.cart_repository.add(db, cart_item)

        cart_item.quantity += quantity
        cart_item.updated_at = now
        shopping_session.last_activity_at = now

        event = self.event_repository.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=EventType.PRODUCT_SCANNED.value,
                source=EventSource.CUSTOMER.value,
                sku=product.sku,
                quantity=quantity,
                correlation_id=str(uuid4()),
                payload={
                    "barcode": product.barcode,
                    "unit_price_minor": product.unit_price_minor,
                    "currency": product.currency,
                },
            ),
        )
        db.flush()
        self.reconciliation_service.reconcile_session(
            db, session_id=session_id, trigger_event_id=event.id, now=now
        )
        digital_cart = self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL)
        result = CartMutationResult(
            operation=operation,
            accepted=True,
            reason="PRODUCT_SCANNED",
            event_id=event.id,
            sku=product.sku,
            quantity_delta=quantity,
            digital_cart=digital_cart,
        )
        self._save_idempotent_result(
            db,
            session_id=session_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result=result,
        )
        db.commit()
        return result

    def remove(
        self,
        db: Session,
        *,
        session_id: str,
        sku: str,
        quantity: int,
        customer_token: str | None,
        idempotency_key: str | None,
    ) -> CartMutationResult:
        shopping_session = self._authorize_customer(
            db,
            session_id=session_id,
            customer_token=customer_token,
        )
        product = self._get_product_by_sku(db, sku)
        idempotency_key = self._validate_idempotency_key(idempotency_key)
        request_fingerprint = self._fingerprint({"sku": product.sku, "quantity": quantity})
        operation = "DIGITAL_REMOVE"

        replay = self._restore_idempotent_result(
            db,
            session_id=session_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if replay is not None:
            return replay

        cart_item = self.cart_repository.get_item(
            db,
            session_id=session_id,
            product_id=product.id,
            source=CartSource.DIGITAL,
        )
        if cart_item is None or cart_item.quantity <= 0:
            raise CartItemNotFound(f"Product '{product.sku}' is not in the digital cart")
        if cart_item.quantity < quantity:
            raise CartQuantityConflict(
                f"Cannot remove {quantity} unit(s); digital cart contains only {cart_item.quantity}"
            )

        now = utcnow()
        cart_item.quantity -= quantity
        cart_item.updated_at = now
        shopping_session.last_activity_at = now

        event = self.event_repository.add(
            db,
            DomainEvent(
                session_id=session_id,
                event_type=EventType.DIGITAL_ITEM_REMOVED.value,
                source=EventSource.CUSTOMER.value,
                sku=product.sku,
                quantity=quantity,
                correlation_id=str(uuid4()),
                payload={"barcode": product.barcode},
            ),
        )
        db.flush()
        self.reconciliation_service.reconcile_session(
            db, session_id=session_id, trigger_event_id=event.id, now=now
        )
        digital_cart = self._cart_read(db, session_id=session_id, source=CartSource.DIGITAL)
        result = CartMutationResult(
            operation=operation,
            accepted=True,
            reason="DIGITAL_ITEM_REMOVED",
            event_id=event.id,
            sku=product.sku,
            quantity_delta=-quantity,
            digital_cart=digital_cart,
        )
        self._save_idempotent_result(
            db,
            session_id=session_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            result=result,
        )
        db.commit()
        return result
