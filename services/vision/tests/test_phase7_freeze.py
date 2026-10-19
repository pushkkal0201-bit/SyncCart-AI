from __future__ import annotations

import numpy as np

from synccart_vision.freeze import FrozenFrameDetector


def frame(value: int) -> np.ndarray:
    return np.full((64, 64, 3), value, dtype=np.uint8)


def test_frozen_frame_detector_trips_after_repeat_limit() -> None:
    detector = FrozenFrameDetector(repeat_limit=3, pixel_epsilon=0.0)
    assert detector.observe(frame(20)) is False
    assert detector.observe(frame(20)) is False
    assert detector.observe(frame(20)) is False
    assert detector.observe(frame(20)) is True
    assert detector.repeat_count == 3


def test_frozen_frame_detector_resets_repeat_counter_on_change() -> None:
    detector = FrozenFrameDetector(repeat_limit=3, pixel_epsilon=0.0)
    detector.observe(frame(20))
    detector.observe(frame(20))
    assert detector.repeat_count == 1
    assert detector.observe(frame(21)) is False
    assert detector.repeat_count == 0
