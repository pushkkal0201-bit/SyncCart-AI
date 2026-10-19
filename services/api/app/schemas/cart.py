from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ScanRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=20)

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str) -> str:
        return value.strip().upper()


class DigitalRemoveRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=20)


class CartLineRead(BaseModel):
    product_id: str
    sku: str
    barcode: str | None
    name: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int
    currency: str
    confidence: float | None = None
    updated_at: datetime


class CartRead(BaseModel):
    source: str
    items: list[CartLineRead]
    distinct_items: int
    total_quantity: int
    totals_by_currency: dict[str, int]


class CartComparisonRead(BaseModel):
    session_id: str
    public_id: str
    session_status: str
    digital_cart: CartRead
    physical_cart: CartRead


class CartMutationResult(BaseModel):
    operation: str
    accepted: bool
    reason: str
    event_id: str | None
    sku: str
    quantity_delta: int
    digital_cart: CartRead
    idempotent_replay: bool = False
