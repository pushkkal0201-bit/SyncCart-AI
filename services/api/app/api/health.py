from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.common import Envelope

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=Envelope[dict[str, str]])
def live(request: Request) -> Envelope[dict[str, str]]:
    return Envelope(data={"status": "alive"}, meta={"request_id": request.state.request_id})


@router.get("/ready", response_model=Envelope[dict[str, str]])
def ready(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Envelope[dict[str, str]]:
    db.execute(text("SELECT 1"))
    return Envelope(
        data={"status": "ready", "database": "ok", "environment": settings.app_env},
        meta={"request_id": request.state.request_id},
    )
