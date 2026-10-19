from __future__ import annotations

from fastapi.testclient import TestClient

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


def simulate_pickup(client: TestClient, session_id: str) -> None:
    response = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers={**SIM_HEADERS, "Idempotency-Key": "pickup-phase4"},
        json={"sku": "SOAP-001", "quantity": 1, "confidence": 0.95},
    )
    assert response.status_code == 200


def force_nudge(client: TestClient, session_id: str) -> dict:
    response = client.post(
        f"/api/v1/simulator/sessions/{session_id}/reconciliation/sweep",
        headers=SIM_HEADERS,
        json={"advance_ms": 150},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_customer_can_acknowledge_scan_now_nudge(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate_pickup(client, session_id)
    state = force_nudge(client, session_id)
    nudge_id = state["latest_nudges"][0]["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/nudges/{nudge_id}/action",
        headers={"X-Session-Token": token},
        json={"action": "SCAN_NOW"},
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["action"] == "SCAN_NOW"
    assert result["nudge_id"] == nudge_id
    assert "Scanner ready" in result["message"]


def test_return_acknowledgement_does_not_fake_physical_return(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate_pickup(client, session_id)
    state = force_nudge(client, session_id)
    nudge_id = state["latest_nudges"][0]["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/nudges/{nudge_id}/action",
        headers={"X-Session-Token": token},
        json={"action": "I_RETURNED_IT"},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["reconciliation"]["cart"]["physical_cart"]["total_quantity"] == 1
    assert result["reconciliation"]["active_discrepancies"]


def test_checkout_approved_only_when_carts_match(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate_pickup(client, session_id)

    blocked = client.post(
        f"/api/v1/sessions/{session_id}/checkout",
        headers={"X-Session-Token": token},
        json={"payment_mode": "SIMULATED"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["data"]["approved"] is False
    assert blocked.json()["data"]["session_status"] == "CHECKOUT_BLOCKED"

    scan = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        headers={"X-Session-Token": token, "Idempotency-Key": "scan-phase4"},
        json={"barcode": "8900000000036", "quantity": 1},
    )
    assert scan.status_code == 200

    approved = client.post(
        f"/api/v1/sessions/{session_id}/checkout",
        headers={"X-Session-Token": token},
        json={"payment_mode": "SIMULATED"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["approved"] is True
    assert approved.json()["data"]["session_status"] == "CHECKOUT_APPROVED"


def test_customer_websocket_streams_reconciliation_snapshot(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    with client.websocket_connect(f"/ws/customer/{session_id}?token={token}") as socket:
        message = socket.receive_json()
    assert message["type"] == "session.snapshot"
    assert message["data"]["session_id"] == session_id
