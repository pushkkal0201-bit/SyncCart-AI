from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import cv2

from synccart_vision.dataops import analyze_frame, dhash, frame_quality_ok, hamming_distance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guided retail-camera dataset capture for SyncCart SKU training")
    parser.add_argument("--source", required=True, help="Webcam index, MJPEG URL, RTSP URL, or video file")
    parser.add_argument("--output", default="runtime/captures")
    parser.add_argument("--session", default=None, help="Capture session name; defaults to timestamp")
    parser.add_argument("--scenario", default="mixed", help="e.g. full_shelf, occlusion, rotated, hand_occlusion")
    parser.add_argument("--every", type=int, default=15, help="Auto-save every N frames")
    parser.add_argument("--auto", action="store_true", help="Start with auto capture enabled")
    parser.add_argument("--max-saved", type=int, default=0, help="Stop after N saved frames; 0 means unlimited")
    parser.add_argument("--min-blur", type=float, default=80.0)
    parser.add_argument("--min-brightness", type=float, default=45.0)
    parser.add_argument("--max-brightness", type=float, default=210.0)
    parser.add_argument("--duplicate-distance", type=int, default=2, help="Reject near-identical dHash frames")
    return parser.parse_args()


def source_value(raw: str) -> int | str:
    return int(raw) if raw.strip().isdigit() else raw.strip()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return cleaned or "capture"


def main() -> None:
    args = parse_args()
    session_name = safe_name(args.session or datetime.now(UTC).strftime("session-%Y%m%dT%H%M%SZ"))
    scenario = safe_name(args.scenario)
    session_dir = Path(args.output) / session_name
    image_dir = session_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = session_dir / "capture_metadata.jsonl"

    capture = cv2.VideoCapture(source_value(args.source))
    if not capture.isOpened():
        raise SystemExit(f"Could not open camera source: {args.source}")

    index = 0
    saved = 0
    rejected_quality = 0
    rejected_duplicate = 0
    auto_enabled = bool(args.auto)
    accepted_hashes: list[str] = []

    print("SPACE = quality-checked save | F = force save | A = toggle auto | Q/ESC = quit")
    print(f"session={session_name} scenario={scenario} output={session_dir}")

    def save_frame(frame, *, forced: bool) -> bool:
        nonlocal saved, rejected_quality, rejected_duplicate
        quality = analyze_frame(frame)
        quality_ok, quality_reasons = frame_quality_ok(
            quality,
            min_blur=args.min_blur,
            min_brightness=args.min_brightness,
            max_brightness=args.max_brightness,
        )
        image_hash = dhash(frame)
        duplicate = any(
            hamming_distance(image_hash, existing) <= max(0, args.duplicate_distance)
            for existing in accepted_hashes[-80:]
        )
        if not forced and not quality_ok:
            rejected_quality += 1
            print(f"rejected quality: {','.join(quality_reasons)}")
            return False
        if not forced and duplicate:
            rejected_duplicate += 1
            print("rejected near-duplicate frame")
            return False

        filename = f"{session_name}__{scenario}__{saved:05d}.jpg"
        path = image_dir / filename
        cv2.imwrite(str(path), frame)
        accepted_hashes.append(image_hash)
        record = {
            "filename": filename,
            "relative_path": str(Path("images") / filename),
            "session": session_name,
            "scenario": scenario,
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "source": str(args.source),
            "frame_index": index,
            "forced": forced,
            "quality": quality.to_dict(),
            "dhash": image_hash,
        }
        with metadata_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        saved += 1
        print(f"saved {path}")
        return True

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                print("Camera read failed")
                break
            index += 1
            quality = analyze_frame(frame)
            quality_ok, reasons = frame_quality_ok(
                quality,
                min_blur=args.min_blur,
                min_brightness=args.min_brightness,
                max_brightness=args.max_brightness,
            )
            preview = frame.copy()
            status = "QUALITY OK" if quality_ok else "+".join(reasons)
            lines = [
                f"frames {index} saved {saved} auto={'ON' if auto_enabled else 'OFF'}",
                f"brightness {quality.brightness_mean:.1f} blur {quality.blur_variance:.1f}",
                status,
                f"rejected quality {rejected_quality} duplicate {rejected_duplicate}",
            ]
            for row, text in enumerate(lines, start=1):
                cv2.putText(
                    preview,
                    text,
                    (16, 28 * row),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.62,
                    (255, 255, 255),
                    2,
                )
            cv2.imshow("SyncCart guided dataset capture", preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("a"):
                auto_enabled = not auto_enabled
                print(f"auto capture {'enabled' if auto_enabled else 'disabled'}")
            if key == 32:
                save_frame(frame, forced=False)
            elif key == ord("f"):
                save_frame(frame, forced=True)
            elif auto_enabled and index % max(args.every, 1) == 0:
                save_frame(frame, forced=False)
            if args.max_saved > 0 and saved >= args.max_saved:
                break
            if key in (ord("q"), 27):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()

    summary = {
        "session": session_name,
        "scenario": scenario,
        "frames_seen": index,
        "frames_saved": saved,
        "rejected_quality": rejected_quality,
        "rejected_duplicate": rejected_duplicate,
        "metadata": str(metadata_path),
    }
    (session_dir / "capture_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
