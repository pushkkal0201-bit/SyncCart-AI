from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_and_read_product(client: TestClient) -> None:
    payload = {
        "sku": "SOAP-001",
        "barcode": "8901234567890",
        "name": "Demo Soap",
        "category": "Personal Care",
        "unit_price_minor": 4500,
        "currency": "INR",
        "expected_visual_class": "soap",
    }
    created = client.post("/api/v1/products", json=payload)
    assert created.status_code == 201
    assert created.json()["data"]["sku"] == "SOAP-001"

    fetched = client.get("/api/v1/products/SOAP-001")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["barcode"] == "8901234567890"


def test_product_conflict(client: TestClient) -> None:
    payload = {"sku": "COKE-001", "name": "Demo Cola", "unit_price_minor": 4000}
    assert client.post("/api/v1/products", json=payload).status_code == 201
    duplicate = client.post("/api/v1/products", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PRODUCT_CONFLICT"
