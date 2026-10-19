from __future__ import annotations

from fastapi.testclient import TestClient

MONITOR_HEADERS = {"X-Monitor-Key": "test-monitor-key"}
SIM_HEADERS = {"X-Simulator-Key": "test-simulator-key"}


def create_product(client: TestClient) -> None:
    response = client.post(
        "/api/v1/products",
        json={
            "sku": "SOAP-001",
            "barcode": "8900000000036",
            "name": "Demo Soap",
            "category": "Demo",
            "unit_price_minor": 4500,
            "currency": "INR",
            "expected_visual_class": "soap",
        },
    )
    assert response.status_code == 201


def create_session(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    data = response.json()["data"]
    return data["id"], data["customer_token"]


def test_monitoring_requires_dedicated_key(client: TestClient) -> None:
    response = client.get("/api/v1/admin/overview")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MONITORING_ACCESS_DENIED"


def test_monitoring_overview_reports_real_platform_counts(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    pickup = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers={**SIM_HEADERS, "Idempotency-Key": "monitor-pickup"},
        json={"sku": "SOAP-001", "quantity": 1, "confidence": 0.91},
    )
    assert pickup.status_code == 200

    response = client.get("/api/v1/admin/overview", headers=MONITOR_HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["metrics"]["total_sessions"] == 1
    assert data["metrics"]["vision_events"] == 1
    assert data["metrics"]["open_discrepancies"] == 1
    assert data["camera"]["status"] == "NOT_CONFIGURED"
    assert data["vision"]["status"] == "NOT_CONFIGURED"
    assert any(event["event_type"] == "VISION_PICKUP" for event in data["recent_events"])


def test_monitoring_accepts_explicit_camera_and_vision_telemetry(client: TestClient) -> None:
    camera = client.post(
        "/api/v1/admin/telemetry/camera",
        headers=MONITOR_HEADERS,
        json={
            "camera_id": "PHONE-1",
            "status": "HEALTHY",
            "source": "Android IP camera",
            "fps": 19.7,
            "frame_latency_ms": 48.0,
            "resolution": "1920x1080",
            "stream_mode": "MJPEG",
            "consecutive_failures": 0,
            "note": "LAN stream stable",
        },
    )
    assert camera.status_code == 200
    assert camera.json()["data"]["camera_id"] == "PHONE-1"

    vision = client.post(
        "/api/v1/admin/telemetry/vision",
        headers=MONITOR_HEADERS,
        json={
            "status": "HEALTHY",
            "model_name": "synccart-sku",
            "model_version": "v001",
            "device": "CPU",
            "fps": 12.4,
            "avg_inference_ms": 71.2,
            "avg_confidence": 0.88,
            "low_confidence_rate": 0.04,
            "detections_by_class": {"soap": 3, "cola": 4},
            "note": "Synthetic telemetry contract test",
        },
    )
    assert vision.status_code == 200

    overview = client.get("/api/v1/admin/overview", headers=MONITOR_HEADERS).json()["data"]
    assert overview["camera"]["status"] == "HEALTHY"
    assert overview["camera"]["fps"] == 19.7
    assert overview["vision"]["model_version"] == "v001"
    assert overview["vision"]["detections_by_class"]["soap"] == 3


def test_monitoring_reconciliation_inspector_uses_real_session_state(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers={**SIM_HEADERS, "Idempotency-Key": "inspect-pickup"},
        json={"sku": "SOAP-001", "quantity": 1, "confidence": 0.93},
    )

    response = client.get(
        f"/api/v1/admin/sessions/{session_id}/reconciliation",
        headers=MONITOR_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reconciliation"]["session_status"] == "VERIFY"
    assert any(event["event_type"] == "VISION_PICKUP" for event in data["events"])


def test_monitoring_websocket_streams_snapshot(client: TestClient) -> None:
    with client.websocket_connect("/ws/admin?key=test-monitor-key") as socket:
        message = socket.receive_json()
    assert message["type"] == "monitoring.snapshot"
    assert "services" in message["data"]
    assert "metrics" in message["data"]
