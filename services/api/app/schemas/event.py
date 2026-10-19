from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    id: str
    session_id: str | None
    event_type: str
    event_version: int
    source: str
    sku: str | None
    quantity: int | None
    confidence: float | None
    correlation_id: str
    causation_id: str | None
    camera_id: str | None
    zone_id: str | None
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
