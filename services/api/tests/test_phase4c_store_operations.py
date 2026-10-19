from __future__ import annotations

from fastapi.testclient import TestClient

STORE_HEADERS = {"X-Store-Key": "test-store-key"}
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


def drive_to_review(client: TestClient, session_id: str) -> str:
    pickup = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers={**SIM_HEADERS, "Idempotency-Key": "retailer-pickup"},
        json={"sku": "SOAP-001", "quantity": 1, "confidence": 0.95},
    )
    assert pickup.status_code == 200

    nudge = client.post(
        f"/api/v1/simulator/sessions/{session_id}/reconciliation/sweep",
        headers=SIM_HEADERS,
        json={"advance_ms": 150},
    )
    assert nudge.status_code == 200
    assert nudge.json()["data"]["session_status"] == "NUDGE"

    review = client.post(
        f"/api/v1/simulator/sessions/{session_id}/reconciliation/sweep",
        headers=SIM_HEADERS,
        json={"advance_ms": 800},
    )
    assert review.status_code == 200
    assert review.json()["data"]["session_status"] == "REVIEW"
    return review.json()["data"]["active_discrepancies"][0]["id"]


def test_store_endpoints_require_store_key(client: TestClient) -> None:
    response = client.get("/api/v1/store/overview")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "STORE_ACCESS_DENIED"


def test_store_overview_reports_operational_state(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    drive_to_review(client, session_id)

    response = client.get("/api/v1/store/overview", headers=STORE_HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["metrics"]["active_sessions"] == 1
    assert data["metrics"]["review_required"] == 1
    assert data["metrics"]["open_discrepancies"] == 1
    assert data["review_queue"][0]["sku"] == "SOAP-001"


def test_store_session_detail_contains_reconciliation_and_timeline(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    drive_to_review(client, session_id)

    response = client.get(f"/api/v1/store/sessions/{session_id}", headers=STORE_HEADERS)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reconciliation"]["session_status"] == "REVIEW"
    assert any(event["event_type"] == "VISION_PICKUP" for event in data["events"])
    assert any(event["event_type"] == "REVIEW_REQUIRED" for event in data["events"])


def test_operator_can_resolve_false_detection_without_faking_customer_scan(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    discrepancy_id = drive_to_review(client, session_id)

    response = client.post(
        f"/api/v1/store/reviews/{discrepancy_id}/resolve",
        headers=STORE_HEADERS,
        json={"action": "FALSE_DETECTION", "note": "Shelf occlusion verified by colleague"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["resolved"] is True
    assert data["reconciliation"]["cart"]["physical_cart"]["total_quantity"] == 0
    assert data["reconciliation"]["cart"]["digital_cart"]["total_quantity"] == 0
    assert data["reconciliation"]["active_discrepancies"] == []

    detail = client.get(f"/api/v1/store/sessions/{session_id}", headers=STORE_HEADERS).json()["data"]
    assert any(event["event_type"] == "REVIEW_RESOLVED" for event in detail["events"])
    assert not any(event["event_type"] == "PRODUCT_SCANNED" for event in detail["events"])


def test_store_websocket_streams_snapshot(client: TestClient) -> None:
    with client.websocket_connect("/ws/store?key=test-store-key") as socket:
        message = socket.receive_json()
    assert message["type"] == "store.snapshot"
    assert "metrics" in message["data"]
