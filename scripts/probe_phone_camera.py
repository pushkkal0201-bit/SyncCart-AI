from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2

from synccart_vision.dataops import analyze_frame, dhash


def parse_source(raw: str) -> int | str:
    return int(raw) if raw.strip().isdigit() else raw.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hackathon helper: probe Phone 1 / webcam camera quality before dataset capture. For CCTV/NVR use probe_camera_source.py.")
    parser.add_argument("--source", required=True, help="Webcam index, MJPEG URL, RTSP URL, or video file")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--output", default="runtime/camera_probe.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    capture = cv2.VideoCapture(parse_source(args.source))
    if not capture.isOpened():
        raise SystemExit(f"Could not open camera source: {args.source}")

    started = time.perf_counter()
    qualities = []
    frame_hashes: list[str] = []
    width = 0
    height = 0
    failures = 0
    read_frames = 0
    try:
        while read_frames < max(1, args.frames):
            ok, frame = capture.read()
            if not ok or frame is None:
                failures += 1
                if failures >= 10:
                    break
                continue
            read_frames += 1
            height, width = frame.shape[:2]
            qualities.append(analyze_frame(frame))
            frame_hashes.append(dhash(frame))
    finally:
        capture.release()

    elapsed = max(time.perf_counter() - started, 1e-6)
    if not qualities:
        raise SystemExit("Camera opened but no readable frames were received")

    unique_hashes = len(set(frame_hashes))
    report = {
        "source": str(args.source),
        "frames_requested": args.frames,
        "frames_read": read_frames,
        "read_failures": failures,
        "measured_read_fps": round(read_frames / elapsed, 2),
        "resolution": {"width": width, "height": height},
        "unique_frame_ratio": round(unique_hashes / len(frame_hashes), 4),
        "quality": {
            "brightness_mean": round(sum(q.brightness_mean for q in qualities) / len(qualities), 2),
            "blur_variance_mean": round(sum(q.blur_variance for q in qualities) / len(qualities), 2),
            "dark_fraction_mean": round(sum(q.dark_fraction for q in qualities) / len(qualities), 4),
            "bright_fraction_mean": round(sum(q.bright_fraction for q in qualities) / len(qualities), 4),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved probe report to {output}")
    if report["unique_frame_ratio"] < 0.2:
        print("WARNING: many frames appear identical; check for a frozen or buffered stream.")


if __name__ == "__main__":
    main()
