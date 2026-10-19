from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.cart import (
    CartComparisonRead,
    CartMutationResult,
    DigitalRemoveRequest,
    ScanRequest,
)
from app.schemas.common import Envelope
from app.schemas.event import EventRead
from app.schemas.shopping_session import SessionCreatedRead, SessionRead
from app.services.cart import CartService
from app.services.sessions import SessionService

router = APIRouter()
session_service = SessionService()
cart_service = CartService()
settings = get_settings()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope[SessionCreatedRead])
def create_session(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> Envelope[SessionCreatedRead]:
    shopping_session, customer_token = session_service.create(db)
    session_data = SessionRead.model_validate(shopping_session).model_dump()
    created = SessionCreatedRead(**session_data, customer_token=customer_token)
    return Envelope(data=created, meta={"request_id": request.state.request_id})


@router.get("", response_model=Envelope[list[SessionRead]])
def list_sessions(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> Envelope[list[SessionRead]]:
    sessions = session_service.list(db)
    return Envelope(
        data=[SessionRead.model_validate(s) for s in sessions],
        meta={"request_id": request.state.request_id},
    )


@router.get("/{session_id}", response_model=Envelope[SessionRead])
def get_session(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[SessionRead]:
    shopping_session = session_service.get(db, session_id)
    return Envelope(
        data=SessionRead.model_validate(shopping_session),
        meta={"request_id": request.state.request_id},
    )


@router.get("/{session_id}/events", response_model=Envelope[list[EventRead]])
def get_session_events(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[list[EventRead]]:
    events = session_service.events(db, session_id)
    return Envelope(
        data=[EventRead.model_validate(e) for e in events],
        meta={"request_id": request.state.request_id},
    )


@router.get("/{session_id}/cart", response_model=Envelope[CartComparisonRead])
def get_cart(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
) -> Envelope[CartComparisonRead]:
    cart = cart_service.get_comparison(
        db,
        session_id=session_id,
        customer_token=customer_token,
    )
    return Envelope(data=cart, meta={"request_id": request.state.request_id})


@router.post("/{session_id}/scan", response_model=Envelope[CartMutationResult])
def scan_product(
    session_id: str,
    payload: ScanRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        Header(alias=settings.idempotency_header),
    ] = None,
) -> Envelope[CartMutationResult]:
    result = cart_service.scan(
        db,
        session_id=session_id,
        barcode=payload.barcode,
        quantity=payload.quantity,
        customer_token=customer_token,
        idempotency_key=idempotency_key,
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})


@router.post(
    "/{session_id}/cart/items/{sku}/remove",
    response_model=Envelope[CartMutationResult],
)
def remove_digital_item(
    session_id: str,
    sku: str,
    payload: DigitalRemoveRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        Header(alias=settings.idempotency_header),
    ] = None,
) -> Envelope[CartMutationResult]:
    result = cart_service.remove(
        db,
        session_id=session_id,
        sku=sku,
        quantity=payload.quantity,
        customer_token=customer_token,
        idempotency_key=idempotency_key,
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})
