from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorBody | None = None

    model_config = ConfigDict(from_attributes=True)
