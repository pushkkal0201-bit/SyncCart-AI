from __future__ import annotations

import time
from uuid import uuid4

from fastapi.testclient import TestClient


def create_product(client: TestClient, *, sku: str = "SOAP-001", barcode: str = "8900000000036") -> dict:
    response = client.post(
        "/api/v1/products",
        json={
            "sku": sku,
            "barcode": barcode,
            "name": "Demo Soap",
            "category": "Personal Care",
            "unit_price_minor": 4500,
            "currency": "INR",
            "expected_visual_class": "soap",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_session(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["customer_token"]
    assert data["customer_token_expires_at"]
    return data["id"], data["customer_token"]


def auth_headers(token: str, *, key: str | None = None) -> dict[str, str]:
    headers = {"X-Session-Token": token}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def test_barcode_lookup(client: TestClient) -> None:
    create_product(client)
    response = client.get("/api/v1/products/barcode/8900000000036")
    assert response.status_code == 200
    assert response.json()["data"]["sku"] == "SOAP-001"


def test_customer_cart_requires_token(client: TestClient) -> None:
    session_id, _ = create_session(client)
    response = client.get(f"/api/v1/sessions/{session_id}/cart")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SESSION_TOKEN"


def test_scan_updates_digital_cart_and_event_history(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)

    response = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 1},
        headers=auth_headers(token, key=str(uuid4())),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accepted"] is True
    assert data["reason"] == "PRODUCT_SCANNED"
    assert data["digital_cart"]["total_quantity"] == 1
    assert data["digital_cart"]["items"][0]["sku"] == "SOAP-001"
    assert data["digital_cart"]["totals_by_currency"]["INR"] == 4500

    events = client.get(f"/api/v1/sessions/{session_id}/events")
    event_types = [event["event_type"] for event in events.json()["data"]]
    assert event_types[:2] == ["SESSION_STARTED", "PRODUCT_SCANNED"]
    assert "DISCREPANCY_OPENED" in event_types


def test_scan_idempotency_does_not_double_add(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    key = str(uuid4())
    request = {"barcode": "8900000000036", "quantity": 1}

    first = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json=request,
        headers=auth_headers(token, key=key),
    )
    second = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json=request,
        headers=auth_headers(token, key=key),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["digital_cart"]["total_quantity"] == 1
    assert second.json()["data"]["digital_cart"]["total_quantity"] == 1
    assert second.json()["data"]["idempotent_replay"] is True


def test_idempotency_key_reuse_with_different_payload_is_rejected(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    key = str(uuid4())

    first = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 1},
        headers=auth_headers(token, key=key),
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 2},
        headers=auth_headers(token, key=key),
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_duplicate_scan_is_suppressed(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)

    first = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 1},
        headers=auth_headers(token, key=str(uuid4())),
    )
    second = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 1},
        headers=auth_headers(token, key=str(uuid4())),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["accepted"] is False
    assert second.json()["data"]["reason"] == "DUPLICATE_SCAN_SUPPRESSED"
    assert second.json()["data"]["digital_cart"]["total_quantity"] == 1


def test_remove_digital_item(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)

    first = client.post(
        f"/api/v1/sessions/{session_id}/scan",
        json={"barcode": "8900000000036", "quantity": 2},
        headers=auth_headers(token, key=str(uuid4())),
    )
    assert first.status_code == 200

    removed = client.post(
        f"/api/v1/sessions/{session_id}/cart/items/SOAP-001/remove",
        json={"quantity": 1},
        headers=auth_headers(token, key=str(uuid4())),
    )
    assert removed.status_code == 200
    assert removed.json()["data"]["quantity_delta"] == -1
    assert removed.json()["data"]["digital_cart"]["total_quantity"] == 1

    events = client.get(f"/api/v1/sessions/{session_id}/events")
    event_types = [event["event_type"] for event in events.json()["data"]]
    assert event_types[-1] == "DIGITAL_ITEM_REMOVED"


def test_cart_returns_both_projections(client: TestClient) -> None:
    create_product(client)
    session_id, token = create_session(client)
    response = client.get(
        f"/api/v1/sessions/{session_id}/cart",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["digital_cart"]["source"] == "DIGITAL"
    assert data["physical_cart"]["source"] == "PHYSICAL"
    assert data["physical_cart"]["items"] == []
