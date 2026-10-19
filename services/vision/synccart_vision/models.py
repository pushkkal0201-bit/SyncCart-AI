from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Detection:
    class_name: str
    sku: str | None
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


@dataclass(frozen=True, slots=True)
class ZoneObservation:
    zone_id: str
    sku: str
    count: int
    confidence: float


@dataclass(frozen=True, slots=True)
class CountTransition:
    zone_id: str
    sku: str
    previous_count: int
    current_count: int
    delta: int
    confidence: float
