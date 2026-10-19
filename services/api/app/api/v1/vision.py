from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.event import EventType
from app.schemas.common import Envelope
from app.schemas.monitoring import CameraTelemetryRead, CameraTelemetryUpdate, VisionTelemetryRead, VisionTelemetryUpdate
from app.schemas.vision import VisionActiveSessionRead, VisionEventIngestRead, VisionEventKind, VisionPhysicalEventRequest
from app.services.monitoring_telemetry import telemetry_store
from app.services.physical_cart import PhysicalCartService
from app.services.vision_auth import VisionAuthService
from app.services.vision_gateway import VisionGatewayService

router = APIRouter()
settings = get_settings()
auth = VisionAuthService()
physical = PhysicalCartService()
gateway = VisionGatewayService()


def authorize(key: str | None) -> None:
    auth.verify(key)


def require_vision_key(
    key: Annotated[str | None, Header(alias=settings.vision_api_key_header)] = None,
) -> None:
    authorize(key)


@router.get(
    "/active-session",
    response_model=Envelope[VisionActiveSessionRead],
    dependencies=[Depends(require_vision_key)],
)
def active_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[VisionActiveSessionRead]:
    return Envelope(data=gateway.active_session(db), meta={"request_id": request.state.request_id})


@router.post(
    "/events",
    response_model=Envelope[VisionEventIngestRead],
    dependencies=[Depends(require_vision_key)],
)
def ingest_event(
    payload: VisionPhysicalEventRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(alias=settings.idempotency_header),
    ] = None,
) -> Envelope[VisionEventIngestRead]:
    event_type = (
        EventType.VISION_PICKUP
        if payload.event_kind == VisionEventKind.PICKUP
        else EventType.VISION_RETURN
    )
    result = physical.mutate(
        db,
        session_id=payload.session_id,
        sku=payload.sku,
        quantity=payload.quantity,
        confidence=payload.confidence,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        event_type=event_type,
        idempotency_key=idempotency_key,
        simulated=False,
        operation_prefix="VISION_WORKER",
        extra_payload={
            "frame_id": payload.frame_id,
            "model_version": payload.model_version,
        },
    )
    return Envelope(
        data=VisionEventIngestRead(event_kind=payload.event_kind, result=result),
        meta={"request_id": request.state.request_id},
    )


@router.post(
    "/telemetry/camera",
    response_model=Envelope[CameraTelemetryRead],
    dependencies=[Depends(require_vision_key)],
)
def update_camera_telemetry(
    payload: CameraTelemetryUpdate,
    request: Request,
) -> Envelope[CameraTelemetryRead]:
    return Envelope(
        data=telemetry_store.update_camera(payload),
        meta={"request_id": request.state.request_id},
    )


@router.post(
    "/telemetry/model",
    response_model=Envelope[VisionTelemetryRead],
    dependencies=[Depends(require_vision_key)],
)
def update_model_telemetry(
    payload: VisionTelemetryUpdate,
    request: Request,
) -> Envelope[VisionTelemetryRead]:
    return Envelope(
        data=telemetry_store.update_vision(payload),
        meta={"request_id": request.state.request_id},
    )
