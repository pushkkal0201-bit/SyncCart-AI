from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.event import EventRead
from app.schemas.reconciliation import ReconciliationRead


class StoreMetricsRead(BaseModel):
    active_sessions: int
    synced_sessions: int
    verifying_sessions: int
    review_required: int
    open_discrepancies: int
    active_nudges: int
    resolved_sessions: int


class StoreSessionSummaryRead(BaseModel):
    session_id: str
    public_id: str
    status: str
    started_at: datetime
    last_activity_at: datetime
    duration_seconds: int
    physical_quantity: int
    digital_quantity: int
    discrepancy_count: int
    consistency_score: float
    primary_issue: str | None = None


class ReviewQueueItemRead(BaseModel):
    discrepancy_id: str
    session_id: str
    public_id: str
    sku: str
    product_name: str
    status: str
    difference: int
    physical_quantity: int
    digital_quantity: int
    risk_score: float
    vision_confidence: float | None
    reason_codes: list[str]
    opened_at: datetime
    updated_at: datetime
    waiting_seconds: int
    nudge_status: str | None = None
    nudge_sent_at: datetime | None = None


class StoreOverviewRead(BaseModel):
    generated_at: datetime
    metrics: StoreMetricsRead
    status_counts: dict[str, int]
    recent_sessions: list[StoreSessionSummaryRead]
    review_queue: list[ReviewQueueItemRead]


class StoreSessionDetailRead(BaseModel):
    reconciliation: ReconciliationRead
    events: list[EventRead]


class ReviewResolutionAction(StrEnum):
    FALSE_DETECTION = "FALSE_DETECTION"
    ITEM_RETURNED_CONFIRMED = "ITEM_RETURNED_CONFIRMED"
    ESCALATE_MANUAL_CHECK = "ESCALATE_MANUAL_CHECK"


class ReviewResolutionRequest(BaseModel):
    action: ReviewResolutionAction
    note: str = Field(default="", max_length=500)


class ReviewResolutionResult(BaseModel):
    discrepancy_id: str
    action: ReviewResolutionAction
    resolved: bool
    message: str
    reconciliation: ReconciliationRead
