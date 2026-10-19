from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.store_ops import (
    ReviewQueueItemRead,
    ReviewResolutionRequest,
    ReviewResolutionResult,
    StoreOverviewRead,
    StoreSessionDetailRead,
    StoreSessionSummaryRead,
)
from app.services.store_auth import StoreAuthService
from app.services.store_operations import StoreOperationsService

router = APIRouter()
settings = get_settings()
auth = StoreAuthService()
operations = StoreOperationsService()


def authorize(store_key: str | None) -> None:
    auth.verify(store_key)


@router.get("/overview", response_model=Envelope[StoreOverviewRead])
def get_overview(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    store_key: Annotated[str | None, Header(alias=settings.store_ops_api_key_header)] = None,
) -> Envelope[StoreOverviewRead]:
    authorize(store_key)
    return Envelope(data=operations.overview(db), meta={"request_id": request.state.request_id})


@router.get("/sessions", response_model=Envelope[list[StoreSessionSummaryRead]])
def list_sessions(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    store_key: Annotated[str | None, Header(alias=settings.store_ops_api_key_header)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> Envelope[list[StoreSessionSummaryRead]]:
    authorize(store_key)
    return Envelope(data=operations.list_sessions(db, limit=limit), meta={"request_id": request.state.request_id})


@router.get("/sessions/{session_id}", response_model=Envelope[StoreSessionDetailRead])
def get_session_detail(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    store_key: Annotated[str | None, Header(alias=settings.store_ops_api_key_header)] = None,
) -> Envelope[StoreSessionDetailRead]:
    authorize(store_key)
    return Envelope(
        data=operations.session_detail(db, session_id=session_id),
        meta={"request_id": request.state.request_id},
    )


@router.get("/reviews", response_model=Envelope[list[ReviewQueueItemRead]])
def list_reviews(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    store_key: Annotated[str | None, Header(alias=settings.store_ops_api_key_header)] = None,
) -> Envelope[list[ReviewQueueItemRead]]:
    authorize(store_key)
    return Envelope(data=operations.review_queue(db), meta={"request_id": request.state.request_id})


@router.post(
    "/reviews/{discrepancy_id}/resolve",
    response_model=Envelope[ReviewResolutionResult],
)
def resolve_review(
    discrepancy_id: str,
    payload: ReviewResolutionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    store_key: Annotated[str | None, Header(alias=settings.store_ops_api_key_header)] = None,
) -> Envelope[ReviewResolutionResult]:
    authorize(store_key)
    result = operations.resolve_review(
        db,
        discrepancy_id=discrepancy_id,
        action=payload.action,
        note=payload.note.strip(),
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})
