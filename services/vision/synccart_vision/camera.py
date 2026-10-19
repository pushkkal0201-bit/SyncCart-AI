from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import cv2
import numpy as np


class CameraError(RuntimeError):
    pass


@dataclass(slots=True)
class CameraFrame:
    image: np.ndarray
    captured_monotonic: float
    frame_id: str


def infer_source_kind(source: str) -> str:
    """Return a stable, non-vendor-specific camera source category."""
    value = source.strip().lower()
    if value.isdigit():
        return "WEBCAM"
    if value.startswith("rtsp://") or value.startswith("rtsps://"):
        return "RTSP_CCTV"
    if value.startswith("http://") or value.startswith("https://"):
        return "HTTP_MJPEG"
    return "VIDEO_FILE"


def redact_camera_source(source: str) -> str:
    """Redact credentials from camera URLs before logging or telemetry."""
    value = source.strip()
    if "://" not in value:
        return value
    try:
        parts = urlsplit(value)
    except ValueError:
        return "<configured-camera-source>"
    if not parts.hostname:
        return "<configured-camera-source>"
    host = parts.hostname
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


class OpenCVCameraSource:
    """OpenCV adapter for retail CCTV/NVR RTSP, MJPEG/HTTP, webcam, or video file.

    The same adapter is used by the hackathon Phone-1 camera profile. Retail
    deployments normally point CAMERA_SOURCE to a CCTV or NVR stream instead.
    """

    def __init__(
        self,
        source: str,
        *,
        camera_id: str,
        backend: str = "AUTO",
        buffer_size: int = 1,
    ) -> None:
        self.source = source
        self.camera_id = camera_id
        self.backend = backend.strip().upper() or "AUTO"
        self.buffer_size = max(0, int(buffer_size))
        self.source_kind = infer_source_kind(source)
        self.safe_source = redact_camera_source(source)
        self._capture: cv2.VideoCapture | None = None
        self._frame_index = 0

    @staticmethod
    def _coerce_source(source: str) -> int | str:
        stripped = source.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped

    def _backend_code(self) -> int | None:
        if self.backend == "AUTO":
            return None
        if self.backend == "FFMPEG":
            return int(cv2.CAP_FFMPEG)
        if self.backend in {"DSHOW", "DIRECTSHOW"}:
            return int(cv2.CAP_DSHOW)
        if self.backend in {"MSMF", "MEDIAFOUNDATION"}:
            return int(cv2.CAP_MSMF)
        raise CameraError(
            f"Unsupported CAMERA_BACKEND={self.backend!r}; use AUTO, FFMPEG, DSHOW, or MSMF"
        )

    def open(self) -> None:
        self.close()
        source = self._coerce_source(self.source)
        backend_code = self._backend_code()
        capture = (
            cv2.VideoCapture(source)
            if backend_code is None
            else cv2.VideoCapture(source, backend_code)
        )
        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Unable to open camera source: {self.safe_source}")
        if self.buffer_size > 0:
            # Backend support varies. Failure to set this hint is non-fatal.
            capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
        self._capture = capture

    def read(self) -> CameraFrame:
        if self._capture is None or not self._capture.isOpened():
            raise CameraError("Camera is not open")
        started = time.perf_counter()
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("Camera frame read failed")
        self._frame_index += 1
        return CameraFrame(
            image=frame,
            captured_monotonic=started,
            frame_id=f"{self.camera_id}-{self._frame_index}",
        )

    def properties(self) -> tuple[int, int, float]:
        if self._capture is None:
            return 0, 0, 0.0
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        return width, height, fps

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
