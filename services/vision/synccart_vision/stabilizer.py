from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from synccart_vision.models import CountTransition, ZoneObservation


@dataclass(slots=True)
class _ZoneState:
    stable_count: int | None = None
    stable_confidence: float = 0.0
    candidate_count: int | None = None
    candidate_confidences: deque[float] = field(default_factory=deque)
    streak: int = 0


class CountStabilizer:
    """Converts noisy per-frame counts into stable shelf count transitions."""

    def __init__(self, required_frames: int = 4) -> None:
        if required_frames < 2:
            raise ValueError("required_frames must be at least 2")
        self.required_frames = required_frames
        self._states: dict[str, _ZoneState] = {}

    def reset(self) -> None:
        self._states.clear()

    def stable_counts(self) -> dict[str, int]:
        return {
            zone_id: state.stable_count
            for zone_id, state in self._states.items()
            if state.stable_count is not None
        }

    def baseline_ready(self, expected_zone_ids: set[str]) -> bool:
        if not expected_zone_ids:
            return False
        return expected_zone_ids.issubset(self.stable_counts().keys())

    def observe(self, observation: ZoneObservation) -> CountTransition | None:
        state = self._states.setdefault(observation.zone_id, _ZoneState())
        if state.candidate_count != observation.count:
            state.candidate_count = observation.count
            state.candidate_confidences.clear()
            state.streak = 0
        state.streak += 1
        state.candidate_confidences.append(observation.confidence)
        while len(state.candidate_confidences) > self.required_frames:
            state.candidate_confidences.popleft()

        if state.streak < self.required_frames:
            return None

        candidate_confidence = (
            sum(state.candidate_confidences) / len(state.candidate_confidences)
            if state.candidate_confidences
            else 0.0
        )

        if state.stable_count is None:
            state.stable_count = observation.count
            state.stable_confidence = candidate_confidence
            return None

        if observation.count == state.stable_count:
            state.stable_confidence = max(state.stable_confidence, candidate_confidence)
            return None

        previous = state.stable_count
        previous_confidence = state.stable_confidence
        state.stable_count = observation.count
        state.stable_confidence = candidate_confidence
        transition_confidence = max(previous_confidence, candidate_confidence)
        return CountTransition(
            zone_id=observation.zone_id,
            sku=observation.sku,
            previous_count=previous,
            current_count=observation.count,
            delta=observation.count - previous,
            confidence=transition_confidence,
        )
