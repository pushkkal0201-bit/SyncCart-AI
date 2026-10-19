from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RuntimeSnapshot:
    service_status: str = "STARTING"
    camera_status: str = "NOT_CONFIGURED"
    vision_status: str = "NOT_CONFIGURED"
    camera_id: str = "EDGE-CAM-01"
    source: str = ""
    resolution: str | None = None
    stream_mode: str | None = None
    fps: float | None = None
    frame_latency_ms: float | None = None
    inference_ms: float | None = None
    avg_confidence: float | None = None
    low_confidence_rate: float | None = None
    model_name: str | None = None
    model_version: str | None = None
    device: str | None = None
    detections_by_class: dict[str, int] = field(default_factory=dict)
    zone_counts: dict[str, int] = field(default_factory=dict)
    last_frame_at: str | None = None
    last_inference_at: str | None = None
    consecutive_failures: int = 0
    freeze_repeat_count: int = 0
    camera_frozen: bool = False
    events_published: int = 0
    events_suppressed: int = 0
    events_skipped_no_session: int = 0
    event_emission_armed: bool = False
    arm_generation: int = 0
    baseline_status: str = "DISARMED"
    last_transition: dict[str, object] | None = None
    last_error: str | None = None
    updated_at: str = field(default_factory=utcnow_iso)


class RuntimeState:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot = RuntimeSnapshot()
        self._latest_jpeg: bytes | None = None

    def update(self, **values: object) -> None:
        with self._lock:
            for key, value in values.items():
                if hasattr(self._snapshot, key):
                    setattr(self._snapshot, key, value)
            self._snapshot.updated_at = utcnow_iso()

    def set_armed(self, armed: bool) -> dict[str, object]:
        """Changes event-emission state and forces a fresh shelf baseline."""
        with self._lock:
            self._snapshot.event_emission_armed = armed
            self._snapshot.arm_generation += 1
            self._snapshot.baseline_status = "LEARNING" if armed else "DISARMED"
            self._snapshot.zone_counts = {}
            self._snapshot.last_transition = None
            self._snapshot.updated_at = utcnow_iso()
            return self._snapshot_dict()

    def _snapshot_dict(self) -> dict[str, object]:
        data = asdict(self._snapshot)
        data["detections_by_class"] = dict(self._snapshot.detections_by_class)
        data["zone_counts"] = dict(self._snapshot.zone_counts)
        data["last_transition"] = (
            dict(self._snapshot.last_transition) if self._snapshot.last_transition else None
        )
        return data

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._snapshot_dict()

    def set_jpeg(self, jpeg: bytes) -> None:
        with self._lock:
            self._latest_jpeg = jpeg

    def jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg


runtime_state = RuntimeState()
