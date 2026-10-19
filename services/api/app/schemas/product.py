from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=120)
    unit_price_minor: int = Field(default=0, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    expected_visual_class: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sku", "barcode")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class ProductRead(BaseModel):
    id: str
    sku: str
    barcode: str | None
    name: str
    category: str | None
    unit_price_minor: int
    currency: str
    expected_visual_class: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
