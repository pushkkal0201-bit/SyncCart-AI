from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_session_writes_start_event(client: TestClient) -> None:
    created = client.post("/api/v1/sessions")
    assert created.status_code == 201
    session = created.json()["data"]
    assert session["public_id"].startswith("SC-")
    assert session["status"] == "ACTIVE"
    assert session["customer_token"]
    assert session["customer_token_expires_at"] is not None

    events = client.get(f"/api/v1/sessions/{session['id']}/events")
    assert events.status_code == 200
    event_data = events.json()["data"]
    assert len(event_data) == 1
    assert event_data[0]["event_type"] == "SESSION_STARTED"


def test_unknown_session_is_standardized_error(client: TestClient) -> None:
    response = client.get("/api/v1/sessions/not-a-real-id")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "SESSION_NOT_FOUND"
