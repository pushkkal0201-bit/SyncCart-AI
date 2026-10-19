from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

SIM_HEADERS = {"X-Simulator-Key": "test-simulator-key"}


def create_product(
    client: TestClient,
    *,
    sku: str = "SOAP-001",
    barcode: str = "8900000000036",
    name: str = "Demo Soap",
) -> dict:
    response = client.post(
        "/api/v1/products",
        json={
            "sku": sku,
            "barcode": barcode,
            "name": name,
            "category": "Demo",
            "unit_price_minor": 4500,
            "currency": "INR",
            "expected_visual_class": sku.lower(),
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_session(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    data = response.json()["data"]
    return data["id"], data["customer_token"]


def customer_headers(token: str) -> dict[str, str]:
    return {"X-Session-Token": token}


def simulate(
    client: TestClient,
    *,
    session_id: str,
    action: str,
    sku: str = "SOAP-001",
    confidence: float = 0.95,
) -> dict:
    headers = {
        **SIM_HEADERS,
        "Idempotency-Key": str(uuid4()),
    }
    response = client.post(
        f"/api/v1/simulator/sessions/{session_id}/{action}",
        headers=headers,
        json={
            "sku": sku,
            "quantity": 1,
            "confidence": confidence,
            "camera_id": "SIM-CAM-01",
            "zone_id": "ZONE-A",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def scan(client: TestClient, *, session_id: str, token: str, barcode: str = "8900000000036") -> dict:
    response = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        headers={
            "X-Session-Token": token,
            "Idempotency-Key": str(uuid4()),
        },
        json={"barcode": barcode, "quantity": 1},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def sweep(client: TestClient, *, session_id: str, advance_ms: int) -> dict:
    response = client.post(
        f"/api/v1/simulator/sessions/{session_id}/reconciliation/sweep",
        headers=SIM_HEADERS,
        json={"advance_ms": advance_ms},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def reconciliation(client: TestClient, *, session_id: str, token: str) -> dict:
    response = client.get(
        f"/api/v1/sessions/{session_id}/reconciliation",
        headers=customer_headers(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_simulator_requires_key(client: TestClient) -> None:
    create_product(client)
    session_id, _ = create_session(client)
    response = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        json={"sku": "SOAP-001", "quantity": 1, "confidence": 0.95},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SIMULATOR_KEY"


def test_low_confidence_physical_event_is_rejected(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    result = simulate(client, session_id=session_id, action="pickup", confidence=0.20)
    assert result["accepted"] is False
    assert result["reason"] == "LOW_VISION_CONFIDENCE_REJECTED"
    status = reconciliation(client, session_id=session_id, token=token)
    assert status["cart"]["physical_cart"]["total_quantity"] == 0
    assert status["active_discrepancies"] == []


def test_pickup_opens_verifying_discrepancy(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    result = simulate(client, session_id=session_id, action="pickup")
    assert result["physical_cart"]["total_quantity"] == 1
    assert result["reconciliation"]["session_status"] == "VERIFY"
    discrepancy = result["reconciliation"]["active_discrepancies"][0]
    assert discrepancy["sku"] == "SOAP-001"
    assert discrepancy["difference"] == 1
    assert discrepancy["status"] == "VERIFYING"

    status = reconciliation(client, session_id=session_id, token=token)
    assert status["cart"]["physical_cart"]["total_quantity"] == 1
    assert status["cart"]["digital_cart"]["total_quantity"] == 0


def test_pickup_then_scan_matches_and_resolves(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    scan(client, session_id=session_id, token=token)

    status = reconciliation(client, session_id=session_id, token=token)
    assert status["session_status"] == "RESOLVED"
    assert status["active_discrepancies"] == []
    assert status["cart"]["physical_cart"]["total_quantity"] == 1
    assert status["cart"]["digital_cart"]["total_quantity"] == 1

    events = client.get(f"/api/v1/sessions/{session_id}/events").json()["data"]
    event_types = [event["event_type"] for event in events]
    assert "MATCH_CONFIRMED" in event_types
    assert "DISCREPANCY_RESOLVED" in event_types


def test_missed_scan_transitions_to_nudge(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    status = sweep(client, session_id=session_id, advance_ms=150)

    assert status["session_status"] == "NUDGE"
    assert status["active_discrepancies"][0]["status"] == "NUDGE_SENT"
    assert status["latest_nudges"][0]["message"] == "Did you forget to scan Demo Soap?"
    assert status["cart_consistency_score"] < 100

    customer_status = reconciliation(client, session_id=session_id, token=token)
    assert customer_status["latest_nudges"][0]["status"] == "SENT"


def test_scan_after_nudge_resolves_discrepancy(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    sweep(client, session_id=session_id, advance_ms=150)
    scan(client, session_id=session_id, token=token)

    status = reconciliation(client, session_id=session_id, token=token)
    assert status["session_status"] == "RESOLVED"
    assert status["active_discrepancies"] == []
    assert status["latest_nudges"][0]["status"] == "RESOLVED"


def test_physical_return_resolves_without_scan(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    sweep(client, session_id=session_id, advance_ms=150)
    returned = simulate(client, session_id=session_id, action="return")

    assert returned["physical_cart"]["total_quantity"] == 0
    status = reconciliation(client, session_id=session_id, token=token)
    assert status["active_discrepancies"] == []
    assert status["session_status"] == "RESOLVED"


def test_scan_before_pickup_is_reconciled_when_physical_event_arrives(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    scan(client, session_id=session_id, token=token)
    first = reconciliation(client, session_id=session_id, token=token)
    assert first["session_status"] == "VERIFY"
    assert first["active_discrepancies"][0]["difference"] == -1

    simulate(client, session_id=session_id, action="pickup")
    final = reconciliation(client, session_id=session_id, token=token)
    assert final["active_discrepancies"] == []
    assert final["session_status"] == "RESOLVED"


def test_unresolved_nudge_escalates_to_review(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    sweep(client, session_id=session_id, advance_ms=150)
    status = sweep(client, session_id=session_id, advance_ms=800)

    assert status["session_status"] == "REVIEW"
    assert status["active_discrepancies"][0]["status"] == "REVIEW_REQUIRED"
    events = client.get(f"/api/v1/sessions/{session_id}/events").json()["data"]
    assert "REVIEW_REQUIRED" in [event["event_type"] for event in events]

    customer_status = reconciliation(client, session_id=session_id, token=token)
    assert customer_status["session_status"] == "REVIEW"



def test_physical_event_idempotency_does_not_double_count(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    key = str(uuid4())
    headers = {**SIM_HEADERS, "Idempotency-Key": key}
    payload = {
        "sku": "SOAP-001",
        "quantity": 1,
        "confidence": 0.95,
        "camera_id": "SIM-CAM-01",
        "zone_id": "ZONE-A",
    }
    first = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers=headers,
        json=payload,
    )
    second = client.post(
        f"/api/v1/simulator/sessions/{session_id}/pickup",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["physical_cart"]["total_quantity"] == 1
    assert second.json()["data"]["physical_cart"]["total_quantity"] == 1
    assert second.json()["data"]["idempotent_replay"] is True

    status = reconciliation(client, session_id=session_id, token=token)
    assert status["cart"]["physical_cart"]["total_quantity"] == 1


def test_discrepancy_history_keeps_resolved_record(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    simulate(client, session_id=session_id, action="pickup")
    scan(client, session_id=session_id, token=token)

    response = client.get(
        f"/api/v1/sessions/{session_id}/discrepancies",
        headers=customer_headers(token),
    )
    assert response.status_code == 200
    history = response.json()["data"]
    assert len(history) == 1
    assert history[0]["status"] == "RESOLVED"
    assert history[0]["difference"] == 0
    assert history[0]["resolved_at"] is not None
