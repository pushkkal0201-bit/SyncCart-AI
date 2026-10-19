from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.cart import CartComparisonRead, CartRead


class DiscrepancyRead(BaseModel):
    id: str
    session_id: str
    sku: str
    status: str
    physical_quantity: int
    digital_quantity: int
    difference: int
    risk_score: float
    vision_confidence: float | None
    reason_codes: list[str]
    correlation_id: str
    opened_at: datetime
    updated_at: datetime
    grace_expires_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NudgeRead(BaseModel):
    id: str
    discrepancy_id: str
    session_id: str
    sku: str
    message: str
    status: str
    sent_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    action: str | None

    model_config = ConfigDict(from_attributes=True)


class ReconciliationRead(BaseModel):
    session_id: str
    public_id: str
    session_status: str
    cart_consistency_score: float = Field(ge=0.0, le=100.0)
    active_discrepancies: list[DiscrepancyRead]
    latest_nudges: list[NudgeRead]
    reasons: list[str]
    cart: CartComparisonRead


class SimulatedPhysicalEventRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=20)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    camera_id: str = Field(default="SIM-CAM-01", min_length=1, max_length=64)
    zone_id: str = Field(default="SIM-ZONE-01", min_length=1, max_length=64)


class SimulatorSweepRequest(BaseModel):
    advance_ms: int = Field(default=0, ge=0, le=300000)


class PhysicalMutationResult(BaseModel):
    operation: str
    accepted: bool
    reason: str
    event_id: str | None
    sku: str
    quantity_delta: int
    physical_cart: CartRead
    reconciliation: ReconciliationRead
    idempotent_replay: bool = False
