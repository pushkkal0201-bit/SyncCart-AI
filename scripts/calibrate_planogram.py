from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import yaml


def parse_source(raw: str) -> int | str:
    return int(raw) if raw.strip().isdigit() else raw.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive SyncCart shelf-zone calibration"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Phone stream URL, webcam index, or image path",
    )
    parser.add_argument(
        "--config",
        default="config/vision_planogram.yaml",
    )
    parser.add_argument(
        "--display-width",
        type=int,
        default=900,
        help="Maximum calibration preview width",
    )
    parser.add_argument(
        "--display-height",
        type=int,
        default=550,
        help="Maximum calibration preview height",
    )
    return parser.parse_args()


def load_frame(source: str):
    path = Path(source)
    if path.exists() and path.is_file():
        frame = cv2.imread(str(path))
        if frame is None:
            raise SystemExit(f"Could not read image: {path}")
        return frame

    capture = cv2.VideoCapture(parse_source(source))
    if not capture.isOpened():
        raise SystemExit(f"Could not open source: {source}")

    try:
        frame = None
        # Warm up network/MJPEG sources so calibration uses a recent frame.
        for _ in range(15):
            ok, candidate = capture.read()
            if ok and candidate is not None:
                frame = candidate
        if frame is None:
            raise SystemExit("Camera opened but no frame could be read")
        return frame
    finally:
        capture.release()


def resize_for_display(frame, max_width: int, max_height: int):
    original_height, original_width = frame.shape[:2]
    scale = min(
        max_width / original_width,
        max_height / original_height,
        1.0,
    )
    new_width = max(1, int(original_width * scale))
    new_height = max(1, int(original_height * scale))
    if scale < 1.0:
        resized = cv2.resize(
            frame,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )
    else:
        resized = frame.copy()
    return resized, scale


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    zones = config.get("zones", [])
    if not zones:
        raise SystemExit("No zones found in planogram config")

    frame = load_frame(args.source)
    original_height, original_width = frame.shape[:2]
    preview, scale = resize_for_display(
        frame,
        args.display_width,
        args.display_height,
    )
    preview_height, preview_width = preview.shape[:2]

    print()
    print("SyncCart Planogram Calibration")
    print("-----------------------------")
    print(f"Original frame: {original_width}x{original_height}")
    print(f"Preview frame: {preview_width}x{preview_height}")
    print()
    print("Draw rectangle around each product.")
    print("Press ENTER or SPACE to confirm.")
    print("Press C to cancel.")
    print()

    calibrated = []
    window_name = "SyncCart Planogram Calibration"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, preview_width, preview_height)

    for zone in zones:
        zone_id = str(zone["zone_id"])
        sku = str(zone["sku"])
        display = preview.copy()
        cv2.putText(
            display,
            f"Select {zone_id} ({sku})",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        x, y, w, h = cv2.selectROI(
            window_name,
            display,
            showCrosshair=True,
            fromCenter=False,
        )
        if w <= 0 or h <= 0:
            cv2.destroyAllWindows()
            raise SystemExit(
                f"Calibration cancelled for {zone_id}; config was not modified"
            )

        original_x = x / scale
        original_y = y / scale
        original_w = w / scale
        original_h = h / scale

        x1 = min(max(original_x / original_width, 0.0), 1.0)
        y1 = min(max(original_y / original_height, 0.0), 1.0)
        x2 = min(max((original_x + original_w) / original_width, 0.0), 1.0)
        y2 = min(max((original_y + original_h) / original_height, 0.0), 1.0)

        calibrated.append(
            {
                "zone_id": zone_id,
                "sku": sku,
                "rect": [
                    round(x1, 6),
                    round(y1, 6),
                    round(x2, 6),
                    round(y2, 6),
                ],
            }
        )
        print(f"Saved {zone_id} -> {sku}")

    cv2.destroyAllWindows()
    config["zones"] = calibrated

    backup = config_path.with_suffix(config_path.suffix + ".bak")
    backup.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    print()
    print("Calibration complete.")
    print(f"Updated: {config_path}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
