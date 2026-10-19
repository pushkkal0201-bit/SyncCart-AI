from __future__ import annotations

from fastapi.testclient import TestClient

VISION_HEADERS = {"X-Vision-Key": "test-vision-key"}


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


def create_session(client: TestClient) -> str:
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_vision_gateway_requires_dedicated_key(client: TestClient) -> None:
    response = client.get("/api/v1/vision/active-session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "VISION_ACCESS_DENIED"


def test_vision_gateway_exposes_only_single_active_session(client: TestClient) -> None:
    response = client.get("/api/v1/vision/active-session", headers=VISION_HEADERS)
    assert response.status_code == 200
    assert response.json()["data"]["available"] is False
    assert response.json()["data"]["reason"] == "NO_ACTIVE_SESSION"

    first = create_session(client)
    response = client.get("/api/v1/vision/active-session", headers=VISION_HEADERS)
    assert response.json()["data"]["available"] is True
    assert response.json()["data"]["session_id"] == first

    create_session(client)
    response = client.get("/api/v1/vision/active-session", headers=VISION_HEADERS)
    assert response.json()["data"]["available"] is False
    assert response.json()["data"]["reason"] == "MULTIPLE_ACTIVE_SESSIONS_UNSUPPORTED_IN_WATCHED_ZONE"


def test_real_vision_event_updates_physical_cart_and_is_not_marked_simulated(client: TestClient) -> None:
    create_product(client)
    session_id = create_session(client)

    response = client.post(
        "/api/v1/vision/events",
        headers={**VISION_HEADERS, "Idempotency-Key": "frame-zone-soap-1"},
        json={
            "session_id": session_id,
            "event_kind": "PICKUP",
            "sku": "SOAP-001",
            "quantity": 1,
            "confidence": 0.94,
            "camera_id": "PHONE-1",
            "zone_id": "SOAP-ZONE",
            "frame_id": "frame-1001",
            "model_version": "synccart-sku-v001",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["event_kind"] == "PICKUP"
    assert data["result"]["accepted"] is True
    assert data["result"]["physical_cart"]["total_quantity"] == 1
    assert data["result"]["reconciliation"]["session_status"] == "VERIFY"

    events = client.get(f"/api/v1/sessions/{session_id}/events").json()["data"]
    pickup = next(event for event in events if event["event_type"] == "VISION_PICKUP")
    assert pickup["payload"]["simulated"] is False
    assert pickup["payload"]["frame_id"] == "frame-1001"
    assert pickup["payload"]["model_version"] == "synccart-sku-v001"


def test_vision_worker_can_publish_camera_and_model_telemetry(client: TestClient) -> None:
    camera = client.post(
        "/api/v1/vision/telemetry/camera",
        headers=VISION_HEADERS,
        json={
            "camera_id": "PHONE-1",
            "status": "HEALTHY",
            "source": "Phone 1 MJPEG",
            "fps": 15.2,
            "frame_latency_ms": 31.0,
            "resolution": "1280x720",
            "stream_mode": "MJPEG",
            "consecutive_failures": 0,
            "note": "Live shelf stream",
        },
    )
    assert camera.status_code == 200

    model = client.post(
        "/api/v1/vision/telemetry/model",
        headers=VISION_HEADERS,
        json={
            "status": "HEALTHY",
            "model_name": "synccart-sku",
            "model_version": "v001",
            "device": "CPU",
            "fps": 9.8,
            "avg_inference_ms": 83.0,
            "avg_confidence": 0.87,
            "low_confidence_rate": 0.05,
            "detections_by_class": {"soap": 3},
            "note": "Custom SKU model loaded",
        },
    )
    assert model.status_code == 200
    assert model.json()["data"]["model_version"] == "v001"
