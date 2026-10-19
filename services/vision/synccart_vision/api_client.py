from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

import httpx

from synccart_vision.models import CountTransition


class CoreApiError(RuntimeError):
    pass


class SyncCartCoreClient:
    def __init__(self, base_url: str, *, api_key: str, api_key_header: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {api_key_header: api_key}
        self._client = httpx.Client(timeout=httpx.Timeout(4.0, connect=2.0))

    def close(self) -> None:
        self._client.close()

    def active_session(self) -> dict[str, object]:
        response = self._client.get(
            f"{self.base_url}/api/v1/vision/active-session",
            headers=self._headers,
        )
        self._raise(response)
        return dict(response.json()["data"])

    def publish_transition(
        self,
        transition: CountTransition,
        *,
        camera_id: str,
        frame_id: str,
        model_version: str,
    ) -> dict[str, object]:
        active = self.active_session()
        if not active.get("available"):
            return {"accepted": False, "reason": active.get("reason", "NO_SESSION")}
        session_id = str(active["session_id"])
        event_kind = "RETURN" if transition.delta > 0 else "PICKUP"
        payload = {
            "session_id": session_id,
            "event_kind": event_kind,
            "sku": transition.sku,
            "quantity": abs(transition.delta),
            "confidence": max(0.0, min(1.0, transition.confidence)),
            "camera_id": camera_id,
            "zone_id": transition.zone_id,
            "frame_id": frame_id,
            "model_version": model_version,
        }
        headers = {**self._headers, "Idempotency-Key": str(uuid4())}
        response = self._client.post(
            f"{self.base_url}/api/v1/vision/events",
            headers=headers,
            json=payload,
        )
        self._raise(response)
        return dict(response.json()["data"])

    def publish_camera_telemetry(self, payload: dict[str, object]) -> None:
        response = self._client.post(
            f"{self.base_url}/api/v1/vision/telemetry/camera",
            headers=self._headers,
            json=payload,
        )
        self._raise(response)

    def publish_vision_telemetry(self, payload: dict[str, object]) -> None:
        response = self._client.post(
            f"{self.base_url}/api/v1/vision/telemetry/model",
            headers=self._headers,
            json=payload,
        )
        self._raise(response)

    @staticmethod
    def _raise(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            body = response.json()
        except ValueError:
            body = response.text
        raise CoreApiError(f"Core API returned {response.status_code}: {body}")
