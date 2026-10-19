from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class VisionSettings(BaseSettings):
    service_name: str = "SyncCart Vision Worker"
    service_version: str = "1.0.0"
    core_api_base_url: str = "http://127.0.0.1:8000"
    vision_api_key: str = ""
    vision_api_key_header: str = "X-Vision-Key"
    vision_control_key: str = ""
    vision_control_key_header: str = "X-Vision-Control-Key"
    vision_events_armed: bool = False

    camera_id: str = "EDGE-CAM-01"
    camera_source: str = "0"
    camera_source_name: str = "Retail Edge Camera"
    camera_stream_mode: str = "AUTO"
    camera_backend: str = "AUTO"
    camera_buffer_size: int = Field(default=1, ge=0, le=32)
    camera_reconnect_delay_ms: int = Field(default=1000, ge=100, le=30000)
    camera_read_timeout_ms: int = Field(default=5000, ge=500, le=60000)
    frozen_frame_limit: int = Field(default=90, ge=10, le=10000)
    frozen_frame_pixel_epsilon: float = Field(default=0.001, ge=0.0, le=5.0)

    planogram_path: Path = REPO_ROOT / "config" / "vision_planogram.yaml"
    detector_mode: str = "AUTO"
    occupancy_similarity_threshold: float = Field(default=0.76, ge=0.40, le=0.99)
    occupancy_warmup_frames: int = Field(default=5, ge=1, le=120)
    occupancy_sample_size: int = Field(default=96, ge=32, le=256)
    yolo_weights: Path = REPO_ROOT / "models" / "weights" / "synccart-sku-v001.pt"
    yolo_device: str = "cpu"
    yolo_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    yolo_iou: float = Field(default=0.45, ge=0.0, le=1.0)
    frame_stride: int = Field(default=1, ge=1, le=60)
    stable_frame_count: int = Field(default=4, ge=2, le=60)
    event_cooldown_ms: int = Field(default=1200, ge=0, le=30000)
    telemetry_interval_ms: int = Field(default=2000, ge=250, le=60000)
    jpeg_quality: int = Field(default=80, ge=30, le=100)
    draw_overlays: bool = True
    vision_run_worker: bool = True

    model_name: str = "synccart-sku"
    model_version: str = "v001"

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> VisionSettings:
    return VisionSettings()
