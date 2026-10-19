from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from synccart_vision.models import Detection, ZoneObservation


@dataclass(frozen=True, slots=True)
class ShelfZone:
    zone_id: str
    sku: str
    rect: tuple[float, float, float, float]

    def contains(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.rect
        return x1 <= x <= x2 and y1 <= y <= y2


@dataclass(frozen=True, slots=True)
class Planogram:
    class_to_sku: dict[str, str]
    zones: tuple[ShelfZone, ...]

    @classmethod
    def load(cls, path: Path) -> "Planogram":
        if not path.exists():
            raise FileNotFoundError(f"Planogram not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        class_to_sku = {
            str(key).strip(): str(value).strip().upper()
            for key, value in (raw.get("class_to_sku") or {}).items()
        }
        zones: list[ShelfZone] = []
        for item in raw.get("zones") or []:
            rect = tuple(float(value) for value in item["rect"])
            if len(rect) != 4 or any(value < 0 or value > 1 for value in rect):
                raise ValueError(f"Zone {item.get('zone_id')} rect must contain four normalized values")
            x1, y1, x2, y2 = rect
            if x1 >= x2 or y1 >= y2:
                raise ValueError(f"Zone {item.get('zone_id')} rect is invalid")
            zones.append(
                ShelfZone(
                    zone_id=str(item["zone_id"]),
                    sku=str(item["sku"]).upper(),
                    rect=(x1, y1, x2, y2),
                )
            )
        if not zones:
            raise ValueError("Planogram must define at least one shelf zone")
        return cls(class_to_sku=class_to_sku, zones=tuple(zones))

    def observations(self, detections: list[Detection], frame_width: int, frame_height: int) -> list[ZoneObservation]:
        per_zone: dict[str, list[Detection]] = {zone.zone_id: [] for zone in self.zones}
        for detection in detections:
            mapped_sku = detection.sku or self.class_to_sku.get(detection.class_name)
            if mapped_sku is None:
                continue
            cx, cy = detection.center
            nx = cx / max(frame_width, 1)
            ny = cy / max(frame_height, 1)
            for zone in self.zones:
                if zone.sku == mapped_sku and zone.contains(nx, ny):
                    per_zone[zone.zone_id].append(detection)
                    break

        observations: list[ZoneObservation] = []
        for zone in self.zones:
            selected = per_zone[zone.zone_id]
            confidence = (
                sum(item.confidence for item in selected) / len(selected)
                if selected
                else 0.0
            )
            observations.append(
                ZoneObservation(
                    zone_id=zone.zone_id,
                    sku=zone.sku,
                    count=len(selected),
                    confidence=confidence,
                )
            )
        return observations
