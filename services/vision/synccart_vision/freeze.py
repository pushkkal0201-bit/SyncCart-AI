from __future__ import annotations

import cv2
import numpy as np


class FrozenFrameDetector:
    """Detects a truly frozen video source using a tiny grayscale fingerprint.

    A retail shelf can be visually static for long periods, so this detector intentionally
    uses a very small pixel-difference epsilon and requires many consecutive repeats before
    declaring the stream frozen. Normal sensor noise is enough to keep a healthy live stream
    from being marked frozen.
    """

    def __init__(self, *, repeat_limit: int = 90, pixel_epsilon: float = 0.001) -> None:
        if repeat_limit < 2:
            raise ValueError("repeat_limit must be at least 2")
        if pixel_epsilon < 0:
            raise ValueError("pixel_epsilon must be non-negative")
        self.repeat_limit = repeat_limit
        self.pixel_epsilon = pixel_epsilon
        self._previous: np.ndarray | None = None
        self._repeat_count = 0

    @property
    def repeat_count(self) -> int:
        return self._repeat_count

    def reset(self) -> None:
        self._previous = None
        self._repeat_count = 0

    def observe(self, frame: np.ndarray) -> bool:
        if frame is None or frame.size == 0:
            self._repeat_count += 1
            return self._repeat_count >= self.repeat_limit

        tiny = cv2.resize(frame, (32, 18), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(tiny, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self._previous is None:
            self._previous = gray
            self._repeat_count = 0
            return False

        difference = float(np.mean(np.abs(gray - self._previous)))
        self._previous = gray
        if difference <= self.pixel_epsilon:
            self._repeat_count += 1
        else:
            self._repeat_count = 0
        return self._repeat_count >= self.repeat_limit
