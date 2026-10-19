from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.reconciliation import DiscrepancyRead, ReconciliationRead
from app.services.customer_auth import CustomerAuthService
from app.services.reconciliation import ReconciliationService
from app.services.sessions import SessionService

router = APIRouter()
settings = get_settings()
reconciliation_service = ReconciliationService()
session_service = SessionService()
auth_service = CustomerAuthService()


def authorize(
    db: Session,
    *,
    session_id: str,
    token: str | None,
) -> None:
    shopping_session = session_service.get(db, session_id)
    auth_service.verify(shopping_session, token)


@router.get("/{session_id}/reconciliation", response_model=Envelope[ReconciliationRead])
def get_reconciliation(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
) -> Envelope[ReconciliationRead]:
    authorize(db, session_id=session_id, token=customer_token)
    result = reconciliation_service.get_status(db, session_id=session_id)
    return Envelope(data=result, meta={"request_id": request.state.request_id})


@router.get(
    "/{session_id}/discrepancies",
    response_model=Envelope[list[DiscrepancyRead]],
)
def get_discrepancies(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
) -> Envelope[list[DiscrepancyRead]]:
    authorize(db, session_id=session_id, token=customer_token)
    items = reconciliation_service.list_discrepancies(db, session_id=session_id)
    return Envelope(
        data=[DiscrepancyRead.model_validate(item) for item in items],
        meta={"request_id": request.state.request_id},
    )
