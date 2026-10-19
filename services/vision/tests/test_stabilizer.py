from __future__ import annotations

from synccart_vision.models import ZoneObservation
from synccart_vision.stabilizer import CountStabilizer


def observation(count: int, confidence: float = 0.9) -> ZoneObservation:
    return ZoneObservation(zone_id="SOAP-ZONE", sku="SOAP-001", count=count, confidence=confidence)


def test_stabilizer_requires_repeated_count_before_baseline_or_transition() -> None:
    stabilizer = CountStabilizer(required_frames=3)
    assert stabilizer.observe(observation(3)) is None
    assert stabilizer.observe(observation(3)) is None
    assert stabilizer.observe(observation(3)) is None

    assert stabilizer.observe(observation(2)) is None
    assert stabilizer.observe(observation(3)) is None
    assert stabilizer.observe(observation(2)) is None
    assert stabilizer.observe(observation(2)) is None
    transition = stabilizer.observe(observation(2))

    assert transition is not None
    assert transition.previous_count == 3
    assert transition.current_count == 2
    assert transition.delta == -1
    assert transition.sku == "SOAP-001"


def test_stabilizer_detects_return_after_stable_increase() -> None:
    stabilizer = CountStabilizer(required_frames=2)
    stabilizer.observe(observation(2))
    stabilizer.observe(observation(2))
    stabilizer.observe(observation(3))
    transition = stabilizer.observe(observation(3))
    assert transition is not None
    assert transition.delta == 1
    assert transition.confidence >= 0.9


def test_stabilizer_reports_baseline_ready_only_after_all_expected_zones() -> None:
    stabilizer = CountStabilizer(required_frames=2)
    soap = ZoneObservation(zone_id="SOAP-ZONE", sku="SOAP-001", count=3, confidence=0.9)
    cola = ZoneObservation(zone_id="COLA-ZONE", sku="COLA-001", count=4, confidence=0.9)
    stabilizer.observe(soap)
    stabilizer.observe(soap)
    assert stabilizer.baseline_ready({"SOAP-ZONE", "COLA-ZONE"}) is False
    stabilizer.observe(cola)
    stabilizer.observe(cola)
    assert stabilizer.baseline_ready({"SOAP-ZONE", "COLA-ZONE"}) is True
    assert stabilizer.stable_counts() == {"SOAP-ZONE": 3, "COLA-ZONE": 4}
