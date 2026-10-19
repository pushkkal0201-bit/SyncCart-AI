from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.event import EventRead
from app.schemas.reconciliation import ReconciliationRead


class ServiceState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ServiceHealthRead(BaseModel):
    name: str
    status: ServiceState
    detail: str
    last_checked_at: datetime


class CameraTelemetryUpdate(BaseModel):
    camera_id: str = Field(min_length=1, max_length=64)
    status: ServiceState
    source: str = Field(default="Retail Edge Camera", max_length=120)
    fps: float | None = Field(default=None, ge=0.0, le=240.0)
    frame_latency_ms: float | None = Field(default=None, ge=0.0, le=120000.0)
    resolution: str | None = Field(default=None, max_length=32)
    stream_mode: str | None = Field(default=None, max_length=32)
    last_frame_at: datetime | None = None
    consecutive_failures: int = Field(default=0, ge=0, le=100000)
    note: str = Field(default="", max_length=500)


class CameraTelemetryRead(CameraTelemetryUpdate):
    updated_at: datetime


class VisionTelemetryUpdate(BaseModel):
    status: ServiceState
    model_name: str | None = Field(default=None, max_length=120)
    model_version: str | None = Field(default=None, max_length=64)
    device: str | None = Field(default=None, max_length=64)
    fps: float | None = Field(default=None, ge=0.0, le=240.0)
    avg_inference_ms: float | None = Field(default=None, ge=0.0, le=120000.0)
    avg_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    low_confidence_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    detections_by_class: dict[str, int] = Field(default_factory=dict)
    last_inference_at: datetime | None = None
    note: str = Field(default="", max_length=500)


class VisionTelemetryRead(VisionTelemetryUpdate):
    updated_at: datetime


class MonitoringMetricsRead(BaseModel):
    total_sessions: int
    active_sessions: int
    total_events: int
    vision_events: int
    customer_scan_events: int
    match_confirmed_events: int
    open_discrepancies: int
    event_matches: int
    nudges_sent: int
    reviews_required: int
    checkouts_approved: int


class MonitoringNoticeRead(BaseModel):
    level: str
    title: str
    detail: str


class MonitoringOverviewRead(BaseModel):
    generated_at: datetime
    services: list[ServiceHealthRead]
    metrics: MonitoringMetricsRead
    camera: CameraTelemetryRead
    vision: VisionTelemetryRead
    recent_events: list[EventRead]
    notices: list[MonitoringNoticeRead]


class MonitoringSessionInspectorRead(BaseModel):
    reconciliation: ReconciliationRead
    events: list[EventRead]
