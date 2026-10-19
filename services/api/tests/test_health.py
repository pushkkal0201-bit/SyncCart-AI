from __future__ import annotations

from fastapi.testclient import TestClient


def test_live_health(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "alive"
    assert response.headers["X-Request-ID"]


def test_ready_health(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "ok"
