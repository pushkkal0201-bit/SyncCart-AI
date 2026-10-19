from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from synccart_vision.models import Detection
from synccart_vision.planogram import Planogram


class Detector(Protocol):
    name: str
    version: str

    def detect(self, frame: np.ndarray) -> list[Detection]: ...


class DetectorUnavailable(RuntimeError):
    pass


class YoloDetector:
    """Ultralytics YOLO adapter with lazy dependency loading."""

    def __init__(
        self,
        weights: Path,
        *,
        device: str,
        confidence: float,
        iou: float,
        class_to_sku: dict[str, str],
        model_name: str,
        model_version: str,
    ) -> None:
        if not weights.exists():
            raise DetectorUnavailable(f"YOLO weights not found: {weights}")
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DetectorUnavailable(
                'Ultralytics is not installed. Run: pip install -e "./services/vision[yolo]"'
            ) from exc
        self._model = YOLO(str(weights))
        self.device = device
        self.confidence = confidence
        self.iou = iou
        self.class_to_sku = class_to_sku
        self.name = model_name
        self.version = model_version

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )
        if not results:
            return []
        result = results[0]
        names = result.names
        detections: list[Detection] = []
        boxes = result.boxes
        if boxes is None:
            return detections
        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = str(names[cls_id])
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            detections.append(
                Detection(
                    class_name=class_name,
                    sku=self.class_to_sku.get(class_name),
                    confidence=confidence,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )
        return detections


class FixedZoneReferenceDetector:
    """Training-free fixed-zone detector for the controlled retail shelf profile.

    SyncCart's hackathon shelf has one configured SKU per calibrated zone. This detector
    learns the initial occupied appearance of each zone from the first few frames and
    later reports whether that same SKU remains present. It provides a complete live
    camera path without committing binary model weights to the repository, while the
    optional YOLO adapter remains available for appearance-based multi-position SKU
    detection.

    The detector intentionally assumes a fixed camera and fixed planogram. That makes it
    ideal for the controlled shelf demonstration and for planogram-constrained retail
    deployments where each facing is known.
    """

    def __init__(
        self,
        planogram: Planogram,
        *,
        similarity_threshold: float = 0.76,
        warmup_frames: int = 5,
        sample_size: int = 96,
        model_name: str = "synccart-fixed-zone-reference",
        model_version: str = "v1",
    ) -> None:
        if not 0.0 < similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be in (0, 1]")
        if warmup_frames < 1:
            raise ValueError("warmup_frames must be >= 1")
        if sample_size < 16:
            raise ValueError("sample_size must be >= 16")

        self.planogram = planogram
        self.similarity_threshold = similarity_threshold
        self.warmup_frames = warmup_frames
        self.sample_size = sample_size
        self.name = model_name
        self.version = model_version
        self.device = "cpu"

        self._reference_sum: dict[str, np.ndarray] = {}
        self._reference: dict[str, np.ndarray] = {}
        self._warmup_seen = 0
        self._class_by_sku = {
            sku.upper(): class_name for class_name, sku in self.planogram.class_to_sku.items()
        }

    @property
    def ready(self) -> bool:
        return self._warmup_seen >= self.warmup_frames and len(self._reference) == len(
            self.planogram.zones
        )

    def reset_reference(self) -> None:
        self._reference_sum.clear()
        self._reference.clear()
        self._warmup_seen = 0

    def _zone_crop(self, frame: np.ndarray, rect: tuple[float, float, float, float]) -> np.ndarray:
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = rect
        px1 = max(0, min(width - 1, int(round(x1 * width))))
        py1 = max(0, min(height - 1, int(round(y1 * height))))
        px2 = max(px1 + 1, min(width, int(round(x2 * width))))
        py2 = max(py1 + 1, min(height, int(round(y2 * height))))
        crop = frame[py1:py2, px1:px2]
        if crop.size == 0:
            raise DetectorUnavailable("Planogram zone produced an empty crop")
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (self.sample_size, self.sample_size), interpolation=cv2.INTER_AREA)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        return cv2.equalizeHist(gray).astype(np.float32)

    @staticmethod
    def _similarity(reference: np.ndarray, current: np.ndarray) -> float:
        intensity = 1.0 - float(np.mean(np.abs(reference - current))) / 255.0

        reference_u8 = np.clip(reference, 0, 255).astype(np.uint8)
        current_u8 = np.clip(current, 0, 255).astype(np.uint8)
        ref_edges = cv2.Canny(reference_u8, 60, 140)
        cur_edges = cv2.Canny(current_u8, 60, 140)
        edge_similarity = 1.0 - float(np.mean(cv2.absdiff(ref_edges, cur_edges))) / 255.0

        score = (0.72 * intensity) + (0.28 * edge_similarity)
        return max(0.0, min(1.0, score))

    def _learn_reference(self, crops: dict[str, np.ndarray]) -> None:
        for zone_id, crop in crops.items():
            if zone_id not in self._reference_sum:
                self._reference_sum[zone_id] = crop.copy()
            else:
                self._reference_sum[zone_id] += crop
        self._warmup_seen += 1
        if self._warmup_seen >= self.warmup_frames:
            self._reference = {
                zone_id: total / float(self._warmup_seen)
                for zone_id, total in self._reference_sum.items()
            }

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if frame is None or frame.size == 0:
            return []

        height, width = frame.shape[:2]
        crops = {zone.zone_id: self._zone_crop(frame, zone.rect) for zone in self.planogram.zones}

        if not self.ready:
            self._learn_reference(crops)
            # The release profile is commissioned with one product in each configured
            # zone. During reference learning we expose those occupied zones so the
            # count stabilizer learns the correct initial physical-cart baseline.
            detections: list[Detection] = []
            for zone in self.planogram.zones:
                x1, y1, x2, y2 = zone.rect
                detections.append(
                    Detection(
                        class_name=self._class_by_sku.get(zone.sku.upper(), zone.sku.lower()),
                        sku=zone.sku,
                        confidence=1.0,
                        x1=x1 * width,
                        y1=y1 * height,
                        x2=x2 * width,
                        y2=y2 * height,
                    )
                )
            return detections

        detections = []
        for zone in self.planogram.zones:
            reference = self._reference[zone.zone_id]
            similarity = self._similarity(reference, crops[zone.zone_id])
            if similarity < self.similarity_threshold:
                continue
            x1, y1, x2, y2 = zone.rect
            detections.append(
                Detection(
                    class_name=self._class_by_sku.get(zone.sku.upper(), zone.sku.lower()),
                    sku=zone.sku,
                    confidence=similarity,
                    x1=x1 * width,
                    y1=y1 * height,
                    x2=x2 * width,
                    y2=y2 * height,
                )
            )
        return detections
