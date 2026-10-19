from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

from app.models.mixins import utcnow
from app.schemas.monitoring import (
    CameraTelemetryRead,
    CameraTelemetryUpdate,
    ServiceState,
    VisionTelemetryRead,
    VisionTelemetryUpdate,
)


@dataclass(slots=True)
class _CameraState:
    camera_id: str = "EDGE-CAM-01"
    status: ServiceState = ServiceState.NOT_CONFIGURED
    source: str = "Retail Edge Camera"
    fps: float | None = None
    frame_latency_ms: float | None = None
    resolution: str | None = None
    stream_mode: str | None = None
    last_frame_at: datetime | None = None
    consecutive_failures: int = 0
    note: str = "No live retail camera telemetry is connected yet."
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class _VisionState:
    status: ServiceState = ServiceState.NOT_CONFIGURED
    model_name: str | None = None
    model_version: str | None = None
    device: str | None = None
    fps: float | None = None
    avg_inference_ms: float | None = None
    avg_confidence: float | None = None
    low_confidence_rate: float | None = None
    detections_by_class: dict[str, int] = field(default_factory=dict)
    last_inference_at: datetime | None = None
    note: str = "No live Vision model is connected yet. Simulator events remain available."
    updated_at: datetime = field(default_factory=utcnow)


class MonitoringTelemetryStore:
    """Thread-safe process-local operational telemetry.

    Camera FPS and model latency are ephemeral runtime measurements, so Phase 4D keeps them
    out of the transactional database. Phase 6 can replace this adapter with Redis/metrics
    storage without changing the monitoring API contract.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._camera = _CameraState()
        self._vision = _VisionState()

    def camera(self) -> CameraTelemetryRead:
        with self._lock:
            state = self._camera
            return CameraTelemetryRead(
                camera_id=state.camera_id,
                status=state.status,
                source=state.source,
                fps=state.fps,
                frame_latency_ms=state.frame_latency_ms,
                resolution=state.resolution,
                stream_mode=state.stream_mode,
                last_frame_at=state.last_frame_at,
                consecutive_failures=state.consecutive_failures,
                note=state.note,
                updated_at=state.updated_at,
            )

    def vision(self) -> VisionTelemetryRead:
        with self._lock:
            state = self._vision
            return VisionTelemetryRead(
                status=state.status,
                model_name=state.model_name,
                model_version=state.model_version,
                device=state.device,
                fps=state.fps,
                avg_inference_ms=state.avg_inference_ms,
                avg_confidence=state.avg_confidence,
                low_confidence_rate=state.low_confidence_rate,
                detections_by_class=dict(state.detections_by_class),
                last_inference_at=state.last_inference_at,
                note=state.note,
                updated_at=state.updated_at,
            )

    def update_camera(self, payload: CameraTelemetryUpdate) -> CameraTelemetryRead:
        with self._lock:
            self._camera = _CameraState(
                camera_id=payload.camera_id,
                status=payload.status,
                source=payload.source,
                fps=payload.fps,
                frame_latency_ms=payload.frame_latency_ms,
                resolution=payload.resolution,
                stream_mode=payload.stream_mode,
                last_frame_at=payload.last_frame_at,
                consecutive_failures=payload.consecutive_failures,
                note=payload.note,
                updated_at=utcnow(),
            )
        return self.camera()

    def update_vision(self, payload: VisionTelemetryUpdate) -> VisionTelemetryRead:
        with self._lock:
            self._vision = _VisionState(
                status=payload.status,
                model_name=payload.model_name,
                model_version=payload.model_version,
                device=payload.device,
                fps=payload.fps,
                avg_inference_ms=payload.avg_inference_ms,
                avg_confidence=payload.avg_confidence,
                low_confidence_rate=payload.low_confidence_rate,
                detections_by_class=dict(payload.detections_by_class),
                last_inference_at=payload.last_inference_at,
                note=payload.note,
                updated_at=utcnow(),
            )
        return self.vision()

    def reset(self) -> tuple[CameraTelemetryRead, VisionTelemetryRead]:
        with self._lock:
            self._camera = _CameraState()
            self._vision = _VisionState()
        return self.camera(), self.vision()


telemetry_store = MonitoringTelemetryStore()
