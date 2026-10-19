from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import Envelope
from app.schemas.event import EventRead
from app.schemas.monitoring import (
    CameraTelemetryRead,
    CameraTelemetryUpdate,
    MonitoringOverviewRead,
    MonitoringSessionInspectorRead,
    VisionTelemetryRead,
    VisionTelemetryUpdate,
)
from app.services.monitoring import MonitoringService
from app.services.monitoring_auth import MonitoringAuthService
from app.services.monitoring_telemetry import telemetry_store

router = APIRouter()
settings = get_settings()
auth = MonitoringAuthService()
monitoring = MonitoringService()


def authorize(key: str | None) -> None:
    auth.verify(key)


@router.get("/overview", response_model=Envelope[MonitoringOverviewRead])
def get_overview(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
) -> Envelope[MonitoringOverviewRead]:
    authorize(key)
    return Envelope(data=monitoring.overview(db), meta={"request_id": request.state.request_id})


@router.get("/events", response_model=Envelope[list[EventRead]])
def list_events(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 80,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
) -> Envelope[list[EventRead]]:
    authorize(key)
    return Envelope(
        data=monitoring.recent_events(db, limit=limit, event_type=event_type),
        meta={"request_id": request.state.request_id},
    )


@router.get(
    "/sessions/{session_id}/reconciliation",
    response_model=Envelope[MonitoringSessionInspectorRead],
)
def inspect_reconciliation(
    session_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
) -> Envelope[MonitoringSessionInspectorRead]:
    authorize(key)
    return Envelope(
        data=monitoring.inspect_session(db, session_id=session_id),
        meta={"request_id": request.state.request_id},
    )


@router.post("/telemetry/camera", response_model=Envelope[CameraTelemetryRead])
def update_camera_telemetry(
    payload: CameraTelemetryUpdate,
    request: Request,
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
) -> Envelope[CameraTelemetryRead]:
    authorize(key)
    return Envelope(data=telemetry_store.update_camera(payload), meta={"request_id": request.state.request_id})


@router.post("/telemetry/vision", response_model=Envelope[VisionTelemetryRead])
def update_vision_telemetry(
    payload: VisionTelemetryUpdate,
    request: Request,
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
) -> Envelope[VisionTelemetryRead]:
    authorize(key)
    return Envelope(data=telemetry_store.update_vision(payload), meta={"request_id": request.state.request_id})


@router.post("/telemetry/reset", response_model=Envelope[dict[str, CameraTelemetryRead | VisionTelemetryRead]])
def reset_telemetry(
    request: Request,
    key: Annotated[str | None, Header(alias=settings.monitoring_api_key_header)] = None,
) -> Envelope[dict[str, CameraTelemetryRead | VisionTelemetryRead]]:
    authorize(key)
    camera, vision = telemetry_store.reset()
    return Envelope(data={"camera": camera, "vision": vision}, meta={"request_id": request.state.request_id})
