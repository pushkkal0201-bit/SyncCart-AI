from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db import session as db_session_module
from app.services.reconciliation import ReconciliationService

logger = logging.getLogger("synccart.reconciliation_worker")


async def run_reconciliation_worker(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    service = ReconciliationService()
    interval_seconds = settings.reconciliation_sweep_interval_ms / 1000.0
    logger.info("reconciliation_worker_started", extra={"interval_ms": settings.reconciliation_sweep_interval_ms})
    try:
        while not stop_event.is_set():
            db = db_session_module.SessionFactory()
            try:
                processed = service.sweep_all(db)
                if processed:
                    logger.debug("reconciliation_sweep_complete", extra={"session_count": processed})
            except Exception:
                db.rollback()
                logger.exception("reconciliation_sweep_failed")
            finally:
                db.close()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                pass
    finally:
        logger.info("reconciliation_worker_stopped")
