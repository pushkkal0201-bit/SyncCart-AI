from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.monitoring import CameraTelemetryRead, CameraTelemetryUpdate, VisionTelemetryRead, VisionTelemetryUpdate
from app.schemas.reconciliation import PhysicalMutationResult


class VisionEventKind(StrEnum):
    PICKUP = "PICKUP"
    RETURN = "RETURN"


class VisionPhysicalEventRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    event_kind: VisionEventKind
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=20)
    confidence: float = Field(ge=0.0, le=1.0)
    camera_id: str = Field(min_length=1, max_length=64)
    zone_id: str = Field(min_length=1, max_length=64)
    frame_id: str | None = Field(default=None, max_length=128)
    model_version: str | None = Field(default=None, max_length=64)


class VisionEventIngestRead(BaseModel):
    event_kind: VisionEventKind
    result: PhysicalMutationResult


class VisionActiveSessionRead(BaseModel):
    available: bool
    reason: str
    session_id: str | None = None
    public_id: str | None = None
    status: str | None = None


class VisionRuntimeTelemetryRead(BaseModel):
    camera: CameraTelemetryRead
    vision: VisionTelemetryRead


class VisionRuntimeTelemetryUpdate(BaseModel):
    camera: CameraTelemetryUpdate | None = None
    vision: VisionTelemetryUpdate | None = None
