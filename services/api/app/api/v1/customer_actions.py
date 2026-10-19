from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.customer_actions import (
    CheckoutRequest,
    CheckoutResult,
    NudgeActionRequest,
    NudgeActionResult,
)
from app.services.customer_actions import CustomerActionService

router = APIRouter()
settings = get_settings()
service = CustomerActionService()


@router.post(
    "/{session_id}/nudges/{nudge_id}/action",
    response_model=Envelope[NudgeActionResult],
)
def respond_to_nudge(
    session_id: str,
    nudge_id: str,
    payload: NudgeActionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
) -> Envelope[NudgeActionResult]:
    result = service.respond_to_nudge(
        db,
        session_id=session_id,
        nudge_id=nudge_id,
        action=payload.action,
        customer_token=customer_token,
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})


@router.post("/{session_id}/checkout", response_model=Envelope[CheckoutResult])
def checkout(
    session_id: str,
    payload: CheckoutRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    customer_token: Annotated[
        str | None,
        Header(alias=settings.customer_session_token_header),
    ] = None,
) -> Envelope[CheckoutResult]:
    # Phase 4 customer app uses payment simulation only. Real PSP integration is intentionally absent.
    _ = payload
    result = service.checkout(db, session_id=session_id, customer_token=customer_token)
    return Envelope(data=result, meta={"request_id": request.state.request_id})
