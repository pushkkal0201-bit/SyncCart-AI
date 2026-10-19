from __future__ import annotations

from pathlib import Path

from synccart_vision.models import Detection
from synccart_vision.planogram import Planogram


def test_planogram_maps_model_classes_to_sku_and_counts_by_zone(tmp_path: Path) -> None:
    config = tmp_path / "planogram.yaml"
    config.write_text(
        """
class_to_sku:
  soap: SOAP-001
zones:
  - zone_id: SOAP-ZONE
    sku: SOAP-001
    rect: [0.0, 0.0, 0.5, 1.0]
""".strip()
    )
    planogram = Planogram.load(config)
    detections = [
        Detection("soap", None, 0.91, 10, 10, 100, 100),
        Detection("soap", None, 0.88, 110, 20, 190, 120),
        Detection("soap", None, 0.95, 700, 20, 790, 120),
    ]
    observations = planogram.observations(detections, frame_width=1000, frame_height=500)
    assert len(observations) == 1
    assert observations[0].sku == "SOAP-001"
    assert observations[0].count == 2
    assert 0.89 <= observations[0].confidence <= 0.91
