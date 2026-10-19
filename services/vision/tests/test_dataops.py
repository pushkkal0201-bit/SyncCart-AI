from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import yaml

from synccart_vision.dataops import (
    analyze_frame,
    dhash,
    frame_quality_ok,
    hamming_distance,
    parse_yolo_line,
    validate_yolo_dataset,
    validate_yolo_values,
)


def test_frame_quality_and_hash() -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (50, 50), (255, 255, 255), -1)
    quality = analyze_frame(image)
    assert 0 <= quality.brightness_mean <= 255
    assert quality.blur_variance > 0
    image_hash = dhash(image)
    assert len(image_hash) == 16
    assert hamming_distance(image_hash, image_hash) == 0


def test_quality_gate_reasons() -> None:
    quality = analyze_frame(np.zeros((32, 32, 3), dtype=np.uint8))
    ok, reasons = frame_quality_ok(quality)
    assert not ok
    assert "FRAME_TOO_DARK" in reasons


def test_yolo_parser_and_validation() -> None:
    values = parse_yolo_line("2 0.5 0.5 0.2 0.2")
    assert values[0] == 2
    assert validate_yolo_values(values, 6) == []
    assert validate_yolo_values((8, 0.5, 0.5, 0.2, 0.2), 6)
    assert validate_yolo_values((0, 0.95, 0.5, 0.2, 0.2), 6)


def test_validate_yolo_dataset_detects_cross_split_duplicate(tmp_path: Path) -> None:
    for split in ("train", "val", "test"):
        (tmp_path / "images" / split).mkdir(parents=True)
        (tmp_path / "labels" / split).mkdir(parents=True)
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.circle(image, (32, 32), 15, (255, 255, 255), -1)
    for split in ("train", "val"):
        cv2.imwrite(str(tmp_path / "images" / split / f"{split}.jpg"), image)
        (tmp_path / "labels" / split / f"{split}.txt").write_text(
            "0 0.5 0.5 0.5 0.5\n", encoding="utf-8"
        )
    config = {
        "path": ".",
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "cola", 1: "chips"},
    }
    config_path = tmp_path / "dataset.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    report = validate_yolo_dataset(config_path)
    assert report.splits["train"].image_count == 1
    assert report.splits["train"].object_count == 1
    assert report.cross_split_duplicate_hashes
    assert not report.valid
