from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB = (REPO_ROOT / "runtime" / "synccart.db").as_posix()


class Settings(BaseSettings):
    app_name: str = "SyncCart AI"
    app_env: str = "development"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{DEFAULT_DB}"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    cors_origin_regex: str = (
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    )
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    request_id_header: str = "X-Request-ID"
    customer_session_token_header: str = "X-Session-Token"
    idempotency_header: str = "Idempotency-Key"
    simulator_api_key_header: str = "X-Simulator-Key"
    store_ops_api_key_header: str = "X-Store-Key"
    monitoring_api_key_header: str = "X-Monitor-Key"
    vision_api_key_header: str = "X-Vision-Key"
    customer_session_token_ttl_minutes: int = Field(default=480, ge=15, le=1440)
    duplicate_scan_window_ms: int = Field(default=1500, ge=0, le=10000)
    scan_grace_period_ms: int = Field(default=4000, ge=100, le=60000)
    event_match_window_ms: int = Field(default=8000, ge=100, le=120000)
    nudge_to_review_ms: int = Field(default=8000, ge=500, le=300000)
    reconciliation_sweep_interval_ms: int = Field(default=500, ge=100, le=10000)
    websocket_snapshot_interval_ms: int = Field(default=500, ge=200, le=5000)
    websocket_heartbeat_ms: int = Field(default=15000, ge=1000, le=120000)
    min_vision_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    enable_reconciliation_worker: bool = True
    enable_simulator: bool = False
    simulator_api_key: str = ""
    store_ops_api_key: str = ""
    monitoring_api_key: str = ""
    vision_api_key: str = ""
    sql_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def ensure_runtime_directory(cls, value: str) -> str:
        url = make_url(value)
        if url.get_backend_name() == "sqlite" and url.database:
            Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
