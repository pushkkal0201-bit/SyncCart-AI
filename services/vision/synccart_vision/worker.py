from __future__ import annotations

import logging
import time
from collections import Counter, deque
from threading import Event

import cv2

from synccart_vision.api_client import CoreApiError, SyncCartCoreClient
from synccart_vision.camera import CameraError, OpenCVCameraSource
from synccart_vision.config import VisionSettings
from synccart_vision.detector import Detector, DetectorUnavailable, FixedZoneReferenceDetector, YoloDetector
from synccart_vision.freeze import FrozenFrameDetector
from synccart_vision.models import CountTransition, Detection
from synccart_vision.overlay import draw_overlay
from synccart_vision.planogram import Planogram
from synccart_vision.runtime import runtime_state, utcnow_iso
from synccart_vision.stabilizer import CountStabilizer

logger = logging.getLogger("synccart.vision")


class VisionWorker:
    def __init__(self, settings: VisionSettings) -> None:
        self.settings = settings
        self.planogram = Planogram.load(settings.planogram_path)
        self.expected_zone_ids = {zone.zone_id for zone in self.planogram.zones}
        self.stabilizer = CountStabilizer(settings.stable_frame_count)
        self.freeze_detector = FrozenFrameDetector(
            repeat_limit=settings.frozen_frame_limit,
            pixel_epsilon=settings.frozen_frame_pixel_epsilon,
        )
        self.camera = OpenCVCameraSource(
            settings.camera_source,
            camera_id=settings.camera_id,
            backend=settings.camera_backend,
            buffer_size=settings.camera_buffer_size,
        )
        self.client = SyncCartCoreClient(
            settings.core_api_base_url,
            api_key=settings.vision_api_key,
            api_key_header=settings.vision_api_key_header,
        )
        self.detector: Detector | None = None
        self._last_event_at: dict[str, float] = {}
        self._fps_samples: deque[float] = deque(maxlen=30)
        self._inference_samples: deque[float] = deque(maxlen=30)
        self._confidence_samples: deque[float] = deque(maxlen=120)
        self._low_confidence_samples: deque[int] = deque(maxlen=120)
        self._frame_counter = 0
        self._last_telemetry = 0.0
        self._arm_generation_seen = -1

    def _load_detector(self) -> None:
        mode = self.settings.detector_mode.strip().upper()
        allowed = {"AUTO", "YOLO", "ZONE_OCCUPANCY", "REFERENCE"}
        if mode not in allowed:
            raise ValueError(f"Unsupported DETECTOR_MODE={self.settings.detector_mode!r}; expected one of {sorted(allowed)}")

        if mode in {"AUTO", "YOLO"}:
            try:
                self.detector = YoloDetector(
                    self.settings.yolo_weights,
                    device=self.settings.yolo_device,
                    confidence=self.settings.yolo_confidence,
                    iou=self.settings.yolo_iou,
                    class_to_sku=self.planogram.class_to_sku,
                    model_name=self.settings.model_name,
                    model_version=self.settings.model_version,
                )
                runtime_state.update(
                    vision_status="HEALTHY",
                    model_name=self.detector.name,
                    model_version=self.detector.version,
                    device=self.settings.yolo_device,
                    last_error=None,
                )
                logger.info("vision_detector_loaded mode=YOLO weights=%s", self.settings.yolo_weights)
                return
            except DetectorUnavailable as exc:
                if mode == "YOLO":
                    self.detector = None
                    runtime_state.update(
                        vision_status="DEGRADED",
                        model_name=self.settings.model_name,
                        model_version=self.settings.model_version,
                        device=self.settings.yolo_device,
                        last_error=str(exc),
                    )
                    logger.warning("vision_model_unavailable: %s", exc)
                    return
                logger.info("yolo_profile_unavailable_falling_back_to_fixed_zone: %s", exc)

        self.detector = FixedZoneReferenceDetector(
            self.planogram,
            similarity_threshold=self.settings.occupancy_similarity_threshold,
            warmup_frames=self.settings.occupancy_warmup_frames,
            sample_size=self.settings.occupancy_sample_size,
        )
        runtime_state.update(
            vision_status="HEALTHY",
            model_name=self.detector.name,
            model_version=self.detector.version,
            device="cpu",
            last_error=None,
        )
        logger.info(
            "vision_detector_loaded mode=ZONE_OCCUPANCY threshold=%.3f warmup=%s",
            self.settings.occupancy_similarity_threshold,
            self.settings.occupancy_warmup_frames,
        )

    def _sync_control_state(self) -> dict[str, object]:
        snapshot = runtime_state.snapshot()
        generation = int(snapshot.get("arm_generation", 0))
        if generation != self._arm_generation_seen:
            self._arm_generation_seen = generation
            self.stabilizer.reset()
            self._last_event_at.clear()
            runtime_state.update(
                zone_counts={},
                baseline_status="LEARNING" if snapshot.get("event_emission_armed") else "DISARMED",
                last_transition=None,
            )
            logger.info(
                "vision_control_generation_applied generation=%s armed=%s",
                generation,
                snapshot.get("event_emission_armed"),
            )
            snapshot = runtime_state.snapshot()
        return snapshot

    def _camera_telemetry(self, status: str, *, note: str) -> dict[str, object]:
        snapshot = runtime_state.snapshot()
        return {
            "camera_id": self.settings.camera_id,
            "status": status,
            "source": self.settings.camera_source_name,
            "fps": snapshot.get("fps"),
            "frame_latency_ms": snapshot.get("frame_latency_ms"),
            "resolution": snapshot.get("resolution"),
            "stream_mode": self.settings.camera_stream_mode,
            "last_frame_at": snapshot.get("last_frame_at"),
            "consecutive_failures": snapshot.get("consecutive_failures", 0),
            "note": note,
        }

    def _vision_telemetry(self, status: str, *, note: str) -> dict[str, object]:
        snapshot = runtime_state.snapshot()
        arm_state = "ARMED" if snapshot.get("event_emission_armed") else "DISARMED"
        baseline = snapshot.get("baseline_status", "UNKNOWN")
        return {
            "status": status,
            "model_name": snapshot.get("model_name") or self.settings.model_name,
            "model_version": snapshot.get("model_version") or self.settings.model_version,
            "device": snapshot.get("device") or self.settings.yolo_device,
            "fps": snapshot.get("fps"),
            "avg_inference_ms": snapshot.get("inference_ms"),
            "avg_confidence": snapshot.get("avg_confidence"),
            "low_confidence_rate": snapshot.get("low_confidence_rate"),
            "detections_by_class": snapshot.get("detections_by_class", {}),
            "last_inference_at": snapshot.get("last_inference_at"),
            "note": f"{note}; events={arm_state}; baseline={baseline}",
        }

    def _publish_telemetry(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_telemetry) * 1000 < self.settings.telemetry_interval_ms:
            return
        self._last_telemetry = now
        snapshot = runtime_state.snapshot()
        try:
            self.client.publish_camera_telemetry(
                self._camera_telemetry(
                    str(snapshot.get("camera_status", "DEGRADED")),
                    note=(
                        f"{self.camera.source_kind} retail camera runtime"
                        if not snapshot.get("camera_frozen")
                        else f"{self.camera.source_kind} stream appears frozen; reconnecting"
                    ),
                )
            )
            self.client.publish_vision_telemetry(
                self._vision_telemetry(
                    str(snapshot.get("vision_status", "DEGRADED")),
                    note=(
                        "Retail shelf detector active"
                        if self.detector is not None
                        else "Vision detector unavailable"
                    ),
                )
            )
        except CoreApiError as exc:
            runtime_state.update(last_error=str(exc))
            logger.warning("telemetry_publish_failed: %s", exc)

    def _suppress_transition(self, transition: CountTransition, *, reason: str) -> None:
        snapshot = runtime_state.snapshot()
        runtime_state.update(
            events_suppressed=int(snapshot.get("events_suppressed", 0)) + 1,
            last_transition={
                "zone_id": transition.zone_id,
                "sku": transition.sku,
                "previous_count": transition.previous_count,
                "current_count": transition.current_count,
                "delta": transition.delta,
                "confidence": transition.confidence,
                "published": False,
                "reason": reason,
                "at": utcnow_iso(),
            },
        )
        logger.info(
            "physical_event_suppressed reason=%s zone=%s sku=%s delta=%s",
            reason,
            transition.zone_id,
            transition.sku,
            transition.delta,
        )

    def _publish_transition(self, transition: CountTransition, *, frame_id: str) -> None:
        snapshot = runtime_state.snapshot()
        if not snapshot.get("event_emission_armed"):
            self._suppress_transition(transition, reason="EVENT_EMISSION_DISARMED")
            return
        if snapshot.get("baseline_status") != "READY":
            self._suppress_transition(transition, reason="BASELINE_NOT_READY")
            return

        now = time.monotonic()
        last = self._last_event_at.get(transition.zone_id, 0.0)
        if (now - last) * 1000 < self.settings.event_cooldown_ms:
            self._suppress_transition(transition, reason="EVENT_COOLDOWN")
            return
        self._last_event_at[transition.zone_id] = now
        try:
            result = self.client.publish_transition(
                transition,
                camera_id=self.settings.camera_id,
                frame_id=frame_id,
                model_version=str(runtime_state.snapshot().get("model_version") or self.settings.model_version),
            )
        except CoreApiError as exc:
            runtime_state.update(last_error=str(exc))
            logger.warning("physical_event_publish_failed: %s", exc)
            return
        if result.get("accepted") is False:
            snapshot = runtime_state.snapshot()
            runtime_state.update(
                events_skipped_no_session=int(snapshot.get("events_skipped_no_session", 0)) + 1,
                last_transition={
                    "zone_id": transition.zone_id,
                    "sku": transition.sku,
                    "previous_count": transition.previous_count,
                    "current_count": transition.current_count,
                    "delta": transition.delta,
                    "confidence": transition.confidence,
                    "published": False,
                    "reason": result.get("reason", "CORE_REJECTED"),
                    "at": utcnow_iso(),
                },
            )
            logger.info("physical_event_skipped reason=%s", result.get("reason"))
            return
        snapshot = runtime_state.snapshot()
        runtime_state.update(
            events_published=int(snapshot.get("events_published", 0)) + 1,
            last_transition={
                "zone_id": transition.zone_id,
                "sku": transition.sku,
                "previous_count": transition.previous_count,
                "current_count": transition.current_count,
                "delta": transition.delta,
                "confidence": transition.confidence,
                "published": True,
                "reason": "PUBLISHED",
                "at": utcnow_iso(),
            },
        )
        logger.info(
            "physical_event_published zone=%s sku=%s delta=%s confidence=%.3f",
            transition.zone_id,
            transition.sku,
            transition.delta,
            transition.confidence,
        )

    def _update_detection_metrics(self, detections: list[Detection], inference_ms: float) -> None:
        self._inference_samples.append(inference_ms)
        by_class = Counter(item.class_name for item in detections)
        for item in detections:
            self._confidence_samples.append(item.confidence)
            self._low_confidence_samples.append(
                int(item.confidence < 0.60)
            )
        runtime_state.update(
            inference_ms=(sum(self._inference_samples) / len(self._inference_samples)),
            avg_confidence=(
                sum(self._confidence_samples) / len(self._confidence_samples)
                if self._confidence_samples
                else None
            ),
            low_confidence_rate=(
                sum(self._low_confidence_samples) / len(self._low_confidence_samples)
                if self._low_confidence_samples
                else None
            ),
            detections_by_class=dict(by_class),
            last_inference_at=utcnow_iso(),
        )

    def _connect_camera(self) -> bool:
        try:
            self.camera.open()
        except CameraError as exc:
            snapshot = runtime_state.snapshot()
            failures = int(snapshot.get("consecutive_failures", 0)) + 1
            runtime_state.update(
                camera_status="OFFLINE",
                service_status="DEGRADED",
                consecutive_failures=failures,
                last_error=str(exc),
            )
            self._publish_telemetry(force=True)
            logger.warning("camera_connect_failed: %s", exc)
            return False
        width, height, _ = self.camera.properties()
        runtime_state.update(
            camera_status="HEALTHY",
            service_status="HEALTHY" if self.detector is not None else "DEGRADED",
            camera_id=self.settings.camera_id,
            source=self.settings.camera_source_name,
            resolution=f"{width}x{height}" if width and height else None,
            stream_mode=self.settings.camera_stream_mode,
            consecutive_failures=0,
            freeze_repeat_count=0,
            camera_frozen=False,
            last_error=None,
        )
        self.stabilizer.reset()
        self.freeze_detector.reset()
        self._publish_telemetry(force=True)
        logger.info(
            "camera_connected id=%s kind=%s source=%s resolution=%sx%s",
            self.settings.camera_id,
            self.camera.source_kind,
            self.camera.safe_source,
            width,
            height,
        )
        return True

    def run(self, stop_event: Event) -> None:
        runtime_state.update(
            service_status="STARTING",
            camera_id=self.settings.camera_id,
            source=self.settings.camera_source_name,
            stream_mode=self.settings.camera_stream_mode,
            model_name=self.settings.model_name,
            model_version=self.settings.model_version,
            device=self.settings.yolo_device,
        )
        self._load_detector()
        try:
            while not stop_event.is_set():
                self._sync_control_state()
                if not self._connect_camera():
                    stop_event.wait(self.settings.camera_reconnect_delay_ms / 1000.0)
                    continue

                while not stop_event.is_set():
                    control = self._sync_control_state()
                    loop_started = time.perf_counter()
                    try:
                        frame = self.camera.read()
                    except CameraError as exc:
                        snapshot = runtime_state.snapshot()
                        failures = int(snapshot.get("consecutive_failures", 0)) + 1
                        runtime_state.update(
                            camera_status="OFFLINE",
                            service_status="DEGRADED",
                            consecutive_failures=failures,
                            last_error=str(exc),
                        )
                        self._publish_telemetry(force=True)
                        self.camera.close()
                        logger.warning("camera_read_failed: %s", exc)
                        break

                    frozen = self.freeze_detector.observe(frame.image)
                    runtime_state.update(
                        freeze_repeat_count=self.freeze_detector.repeat_count,
                        camera_frozen=frozen,
                    )
                    if frozen:
                        runtime_state.update(
                            camera_status="DEGRADED",
                            service_status="DEGRADED",
                            last_error="Camera stream repeated the same frame beyond the freeze threshold",
                        )
                        self._publish_telemetry(force=True)
                        self.camera.close()
                        logger.warning(
                            "camera_stream_frozen repeats=%s; reconnecting",
                            self.freeze_detector.repeat_count,
                        )
                        break

                    self._frame_counter += 1
                    frame_latency_ms = (time.perf_counter() - frame.captured_monotonic) * 1000.0
                    detections: list[Detection] = []
                    observations = []
                    transitions: list[CountTransition] = []
                    if self.detector is not None and self._frame_counter % self.settings.frame_stride == 0:
                        infer_started = time.perf_counter()
                        try:
                            detections = self.detector.detect(frame.image)
                        except Exception as exc:  # model runtime errors must fail safe
                            runtime_state.update(
                                vision_status="DEGRADED",
                                service_status="DEGRADED",
                                last_error=f"Vision inference failed: {exc}",
                            )
                            logger.exception("vision_inference_failed")
                            detections = []
                        inference_ms = (time.perf_counter() - infer_started) * 1000.0
                        self._update_detection_metrics(detections, inference_ms)
                        height, width = frame.image.shape[:2]
                        observations = self.planogram.observations(detections, width, height)
                        for observation in observations:
                            transition = self.stabilizer.observe(observation)
                            if transition is not None and transition.delta != 0:
                                transitions.append(transition)

                        stable_counts = self.stabilizer.stable_counts()
                        baseline_ready = self.stabilizer.baseline_ready(self.expected_zone_ids)
                        if control.get("event_emission_armed"):
                            baseline_status = "READY" if baseline_ready else "LEARNING"
                        else:
                            baseline_status = "DISARMED"
                        runtime_state.update(
                            zone_counts=stable_counts,
                            baseline_status=baseline_status,
                        )
                        for transition in transitions:
                            self._publish_transition(transition, frame_id=frame.frame_id)

                    rendered = (
                        draw_overlay(
                            frame.image,
                            detections=detections,
                            observations=observations,
                            planogram=self.planogram,
                        )
                        if self.settings.draw_overlays
                        else frame.image
                    )
                    ok, jpeg = cv2.imencode(
                        ".jpg",
                        rendered,
                        [int(cv2.IMWRITE_JPEG_QUALITY), self.settings.jpeg_quality],
                    )
                    if ok:
                        runtime_state.set_jpeg(jpeg.tobytes())

                    elapsed = max(time.perf_counter() - loop_started, 1e-6)
                    self._fps_samples.append(1.0 / elapsed)
                    height, width = frame.image.shape[:2]
                    runtime_state.update(
                        camera_status="HEALTHY",
                        vision_status="HEALTHY" if self.detector is not None else "DEGRADED",
                        service_status="HEALTHY" if self.detector is not None else "DEGRADED",
                        resolution=f"{width}x{height}",
                        fps=min(sum(self._fps_samples) / len(self._fps_samples), 240.0),
                        frame_latency_ms=frame_latency_ms,
                        last_frame_at=utcnow_iso(),
                        consecutive_failures=0,
                        camera_frozen=False,
                    )
                    self._publish_telemetry()
        finally:
            self.camera.close()
            self.client.close()
            runtime_state.update(camera_status="OFFLINE", service_status="OFFLINE")
            logger.info("vision_worker_stopped")
