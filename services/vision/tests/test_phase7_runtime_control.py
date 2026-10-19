from __future__ import annotations

from synccart_vision.runtime import RuntimeState


def test_arming_requires_fresh_baseline_and_increments_generation() -> None:
    state = RuntimeState()
    initial = state.snapshot()
    armed = state.set_armed(True)
    assert armed["event_emission_armed"] is True
    assert armed["baseline_status"] == "LEARNING"
    assert armed["arm_generation"] == initial["arm_generation"] + 1

    state.update(zone_counts={"SOAP-ZONE": 3}, baseline_status="READY")
    rearmed = state.set_armed(True)
    assert rearmed["baseline_status"] == "LEARNING"
    assert rearmed["zone_counts"] == {}
    assert rearmed["arm_generation"] == armed["arm_generation"] + 1


def test_disarming_keeps_inference_state_but_blocks_event_gate() -> None:
    state = RuntimeState()
    state.set_armed(True)
    state.update(zone_counts={"SOAP-ZONE": 3}, baseline_status="READY", vision_status="HEALTHY")
    disarmed = state.set_armed(False)
    assert disarmed["event_emission_armed"] is False
    assert disarmed["baseline_status"] == "DISARMED"
    assert disarmed["vision_status"] == "HEALTHY"
