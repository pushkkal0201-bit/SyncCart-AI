from __future__ import annotations

from pathlib import Path

import pytest

from synccart_vision.detector import DetectorUnavailable, YoloDetector


def test_yolo_detector_fails_safe_when_custom_weights_are_missing(tmp_path: Path) -> None:
    with pytest.raises(DetectorUnavailable, match="weights not found"):
        YoloDetector(
            tmp_path / "missing.pt",
            device="cpu",
            confidence=0.55,
            iou=0.45,
            class_to_sku={"soap": "SOAP-001"},
            model_name="synccart-sku",
            model_version="v001",
        )


def test_fixed_zone_reference_detector_tracks_presence_without_model_weights(tmp_path: Path) -> None:
    import cv2
    import numpy as np

    from synccart_vision.detector import FixedZoneReferenceDetector
    from synccart_vision.planogram import Planogram

    config = tmp_path / "planogram.yaml"
    config.write_text(
        """
class_to_sku:
  bottle: BOTTLE-001
zones:
  - zone_id: BOTTLE-ZONE
    sku: BOTTLE-001
    rect: [0.0, 0.0, 1.0, 1.0]
""".strip(),
        encoding="utf-8",
    )
    planogram = Planogram.load(config)
    detector = FixedZoneReferenceDetector(
        planogram,
        similarity_threshold=0.90,
        warmup_frames=2,
        sample_size=64,
    )

    occupied = np.full((160, 160, 3), 235, dtype=np.uint8)
    cv2.rectangle(occupied, (50, 20), (110, 145), (40, 40, 120), -1)
    cv2.circle(occupied, (80, 18), 18, (30, 30, 100), -1)

    assert len(detector.detect(occupied)) == 1
    assert len(detector.detect(occupied)) == 1
    assert detector.ready is True
    assert len(detector.detect(occupied)) == 1

    empty = np.full((160, 160, 3), 235, dtype=np.uint8)
    assert detector.detect(empty) == []
