from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.event import EventType
from app.models.mixins import utcnow
from app.schemas.common import Envelope
from app.schemas.reconciliation import (
    PhysicalMutationResult,
    ReconciliationRead,
    SimulatedPhysicalEventRequest,
    SimulatorSweepRequest,
)
from app.services.physical_cart import PhysicalCartService
from app.services.reconciliation import ReconciliationService
from app.services.simulator_auth import SimulatorAuthService

router = APIRouter()
settings = get_settings()
physical_service = PhysicalCartService()
reconciliation_service = ReconciliationService()
simulator_auth = SimulatorAuthService()


def require_simulator_key(
    simulator_key: Annotated[
        str | None,
        Header(alias=settings.simulator_api_key_header),
    ] = None,
) -> None:
    simulator_auth.verify(simulator_key)


@router.post(
    "/sessions/{session_id}/pickup",
    response_model=Envelope[PhysicalMutationResult],
    dependencies=[Depends(require_simulator_key)],
)
def simulate_pickup(
    session_id: str,
    payload: SimulatedPhysicalEventRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(alias=settings.idempotency_header),
    ] = None,
) -> Envelope[PhysicalMutationResult]:
    result = physical_service.mutate(
        db,
        session_id=session_id,
        sku=payload.sku,
        quantity=payload.quantity,
        confidence=payload.confidence,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        event_type=EventType.VISION_PICKUP,
        idempotency_key=idempotency_key,
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})


@router.post(
    "/sessions/{session_id}/return",
    response_model=Envelope[PhysicalMutationResult],
    dependencies=[Depends(require_simulator_key)],
)
def simulate_return(
    session_id: str,
    payload: SimulatedPhysicalEventRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(alias=settings.idempotency_header),
    ] = None,
) -> Envelope[PhysicalMutationResult]:
    result = physical_service.mutate(
        db,
        session_id=session_id,
        sku=payload.sku,
        quantity=payload.quantity,
        confidence=payload.confidence,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        event_type=EventType.VISION_RETURN,
        idempotency_key=idempotency_key,
    )
    return Envelope(data=result, meta={"request_id": request.state.request_id})


@router.post(
    "/sessions/{session_id}/reconciliation/sweep",
    response_model=Envelope[ReconciliationRead],
    dependencies=[Depends(require_simulator_key)],
)
def sweep_session(
    session_id: str,
    payload: SimulatorSweepRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ReconciliationRead]:
    now = utcnow() + timedelta(milliseconds=payload.advance_ms)
    result = reconciliation_service.sweep_session(db, session_id=session_id, now=now)
    db.commit()
    return Envelope(data=result, meta={"request_id": request.state.request_id})
