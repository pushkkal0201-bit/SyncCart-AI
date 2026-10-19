from __future__ import annotations

import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Event, Thread

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse

from synccart_vision.config import get_settings
from synccart_vision.runtime import runtime_state
from synccart_vision.worker import VisionWorker

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("synccart.vision.api")


def _require_control_key(value: str | None) -> None:
    if not settings.vision_control_key:
        raise HTTPException(status_code=503, detail="Vision control key is not configured")
    if value is None or not hmac.compare_digest(value, settings.vision_control_key):
        raise HTTPException(status_code=401, detail="Invalid Vision control key")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop_event = Event()
    thread: Thread | None = None
    runtime_state.set_armed(settings.vision_events_armed)
    if settings.vision_run_worker:
        worker = VisionWorker(settings)
        thread = Thread(target=worker.run, args=(stop_event,), name="synccart-vision-worker", daemon=True)
        thread.start()
    try:
        yield
    finally:
        stop_event.set()
        if thread is not None:
            thread.join(timeout=5.0)


app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description=(
        "Edge-first retail camera ingestion (CCTV/NVR in production, Phone 1 in the hackathon demo), SKU detection, shelf-count stabilization, "
        "commissioning controls, and live preview service."
    ),
    lifespan=lifespan,
)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "preview": "/preview.mjpeg",
        "health": "/health/ready",
        "control": "/control/status",
    }


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> dict[str, object]:
    snapshot = runtime_state.snapshot()
    return {
        "status": snapshot["service_status"],
        "camera": snapshot["camera_status"],
        "vision": snapshot["vision_status"],
        "armed": snapshot["event_emission_armed"],
        "baseline": snapshot["baseline_status"],
        "camera_frozen": snapshot["camera_frozen"],
        "last_error": snapshot["last_error"],
    }


@app.get("/metrics")
def metrics() -> dict[str, object]:
    return runtime_state.snapshot()


@app.get("/control/status")
def control_status() -> dict[str, object]:
    snapshot = runtime_state.snapshot()
    return {
        "event_emission_armed": snapshot["event_emission_armed"],
        "baseline_status": snapshot["baseline_status"],
        "zone_counts": snapshot["zone_counts"],
        "last_transition": snapshot["last_transition"],
        "events_published": snapshot["events_published"],
        "events_suppressed": snapshot["events_suppressed"],
    }


@app.post("/control/arm")
def arm(
    control_key: str | None = Header(default=None, alias=settings.vision_control_key_header),
) -> dict[str, object]:
    _require_control_key(control_key)
    snapshot = runtime_state.set_armed(True)
    logger.info("vision_event_emission_armed generation=%s", snapshot["arm_generation"])
    return {
        "armed": True,
        "baseline_status": snapshot["baseline_status"],
        "message": "Event emission armed. A fresh stable shelf baseline is required before physical events are published.",
    }


@app.post("/control/disarm")
def disarm(
    control_key: str | None = Header(default=None, alias=settings.vision_control_key_header),
) -> dict[str, object]:
    _require_control_key(control_key)
    snapshot = runtime_state.set_armed(False)
    logger.info("vision_event_emission_disarmed generation=%s", snapshot["arm_generation"])
    return {
        "armed": False,
        "baseline_status": snapshot["baseline_status"],
        "message": "Event emission disarmed. Camera and inference continue for safe commissioning.",
    }


@app.get("/snapshot.jpg")
def snapshot() -> Response:
    jpeg = runtime_state.jpeg()
    if jpeg is None:
        raise HTTPException(status_code=503, detail="No camera frame is available yet")
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/preview.mjpeg")
def preview() -> StreamingResponse:
    def stream():
        last_frame: bytes | None = None
        while True:
            jpeg = runtime_state.jpeg()
            if jpeg is None or jpeg == last_frame:
                import time

                time.sleep(0.05)
                continue
            last_frame = jpeg
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )
