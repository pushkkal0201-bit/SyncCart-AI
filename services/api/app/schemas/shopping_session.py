from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    id: str
    public_id: str
    status: str
    started_at: datetime
    last_activity_at: datetime
    checkout_requested_at: datetime | None
    completed_at: datetime | None
    customer_token_expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionCreatedRead(SessionRead):
    customer_token: str
