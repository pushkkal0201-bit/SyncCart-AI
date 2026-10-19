from __future__ import annotations

import cv2
import numpy as np

from synccart_vision.models import Detection, ZoneObservation
from synccart_vision.planogram import Planogram


def draw_overlay(
    frame: np.ndarray,
    *,
    detections: list[Detection],
    observations: list[ZoneObservation],
    planogram: Planogram,
) -> np.ndarray:
    canvas = frame.copy()
    height, width = canvas.shape[:2]
    count_map = {item.zone_id: item.count for item in observations}

    for zone in planogram.zones:
        x1, y1, x2, y2 = zone.rect
        p1 = (int(x1 * width), int(y1 * height))
        p2 = (int(x2 * width), int(y2 * height))
        cv2.rectangle(canvas, p1, p2, (255, 255, 255), 1)
        label = f"{zone.zone_id} | {zone.sku} | count {count_map.get(zone.zone_id, 0)}"
        cv2.putText(
            canvas,
            label,
            (p1[0] + 6, max(20, p1[1] + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    for detection in detections:
        p1 = (int(detection.x1), int(detection.y1))
        p2 = (int(detection.x2), int(detection.y2))
        cv2.rectangle(canvas, p1, p2, (0, 232, 255), 2)
        label = f"{detection.sku or detection.class_name} {detection.confidence:.2f}"
        cv2.putText(
            canvas,
            label,
            (p1[0], max(18, p1[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 232, 255),
            1,
            cv2.LINE_AA,
        )
    return canvas
