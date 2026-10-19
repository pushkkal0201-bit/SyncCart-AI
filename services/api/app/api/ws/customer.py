from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.db import session as db_session_module
from app.services.customer_auth import CustomerAuthService
from app.services.reconciliation import ReconciliationService
from app.services.sessions import SessionService

router = APIRouter()
settings = get_settings()
auth = CustomerAuthService()
sessions = SessionService()
reconciliation = ReconciliationService()


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.websocket("/customer/{session_id}")
async def customer_socket(websocket: WebSocket, session_id: str, token: str = "") -> None:
    with db_session_module.SessionFactory() as db:
        try:
            shopping_session = sessions.get(db, session_id)
            auth.verify(shopping_session, token)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    previous: str | None = None
    heartbeat_elapsed = 0
    interval = settings.websocket_snapshot_interval_ms / 1000
    try:
        while True:
            with db_session_module.SessionFactory() as db:
                snapshot = reconciliation.get_status(db, session_id=session_id)
                payload = snapshot.model_dump(mode="json")
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            if serialized != previous:
                await websocket.send_json(
                    {
                        "type": "session.snapshot",
                        "version": 1,
                        "timestamp": utc_iso(),
                        "data": payload,
                    }
                )
                previous = serialized
            heartbeat_elapsed += settings.websocket_snapshot_interval_ms
            if heartbeat_elapsed >= settings.websocket_heartbeat_ms:
                await websocket.send_json(
                    {
                        "type": "heartbeat",
                        "version": 1,
                        "timestamp": utc_iso(),
                        "data": {"session_id": session_id},
                    }
                )
                heartbeat_elapsed = 0
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return
