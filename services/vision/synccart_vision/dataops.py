from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
import yaml

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(slots=True)
class FrameQuality:
    brightness_mean: float
    blur_variance: float
    dark_fraction: float
    bright_fraction: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class LabelIssue:
    file: str
    line: int | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SplitReport:
    split: str
    image_count: int = 0
    labelled_image_count: int = 0
    object_count: int = 0
    class_counts: dict[str, int] = field(default_factory=dict)
    missing_labels: list[str] = field(default_factory=list)
    invalid_labels: list[LabelIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "split": self.split,
            "image_count": self.image_count,
            "labelled_image_count": self.labelled_image_count,
            "object_count": self.object_count,
            "class_counts": dict(self.class_counts),
            "missing_labels": list(self.missing_labels),
            "invalid_labels": [issue.to_dict() for issue in self.invalid_labels],
        }


@dataclass(slots=True)
class DatasetReport:
    dataset_yaml: str
    class_names: list[str]
    splits: dict[str, SplitReport]
    duplicate_hashes: dict[str, list[str]] = field(default_factory=dict)
    cross_split_duplicate_hashes: dict[str, list[str]] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not any(
            report.missing_labels or report.invalid_labels for report in self.splits.values()
        ) and not self.cross_split_duplicate_hashes

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_yaml": self.dataset_yaml,
            "class_names": self.class_names,
            "valid": self.valid,
            "splits": {name: report.to_dict() for name, report in self.splits.items()},
            "duplicate_hashes": self.duplicate_hashes,
            "cross_split_duplicate_hashes": self.cross_split_duplicate_hashes,
        }


def analyze_frame(image: np.ndarray) -> FrameQuality:
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    brightness = float(np.mean(gray))
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    dark_fraction = float(np.mean(gray <= 20))
    bright_fraction = float(np.mean(gray >= 235))
    return FrameQuality(
        brightness_mean=brightness,
        blur_variance=blur,
        dark_fraction=dark_fraction,
        bright_fraction=bright_fraction,
    )


def frame_quality_ok(
    quality: FrameQuality,
    *,
    min_blur: float = 80.0,
    min_brightness: float = 45.0,
    max_brightness: float = 210.0,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if quality.blur_variance < min_blur:
        reasons.append("BLUR_TOO_HIGH")
    if quality.brightness_mean < min_brightness:
        reasons.append("FRAME_TOO_DARK")
    if quality.brightness_mean > max_brightness:
        reasons.append("FRAME_TOO_BRIGHT")
    return not reasons, reasons


def dhash(image: np.ndarray, hash_size: int = 8) -> str:
    if image is None or image.size == 0:
        raise ValueError("image must be non-empty")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    width = max(1, (hash_size * hash_size + 3) // 4)
    return f"{value:0{width}x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    if len(hash_a) != len(hash_b):
        raise ValueError("hashes must have the same length")
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def list_images(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def parse_yolo_line(line: str) -> tuple[int, float, float, float, float]:
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError("YOLO label must contain exactly 5 fields")
    class_id = int(parts[0])
    x_center, y_center, width, height = (float(value) for value in parts[1:])
    return class_id, x_center, y_center, width, height


def validate_yolo_values(
    values: tuple[int, float, float, float, float], class_count: int
) -> list[str]:
    class_id, x_center, y_center, width, height = values
    issues: list[str] = []
    if class_id < 0 or class_id >= class_count:
        issues.append(f"class_id {class_id} outside [0, {class_count - 1}]")
    if not 0.0 <= x_center <= 1.0:
        issues.append("x_center outside [0, 1]")
    if not 0.0 <= y_center <= 1.0:
        issues.append("y_center outside [0, 1]")
    if not 0.0 < width <= 1.0:
        issues.append("width outside (0, 1]")
    if not 0.0 < height <= 1.0:
        issues.append("height outside (0, 1]")
    if x_center - width / 2 < 0.0 or x_center + width / 2 > 1.0:
        issues.append("box exceeds image horizontally")
    if y_center - height / 2 < 0.0 or y_center + height / 2 > 1.0:
        issues.append("box exceeds image vertically")
    return issues


def _class_names(raw_names: object) -> list[str]:
    if isinstance(raw_names, dict):
        return [str(raw_names[index]) for index in sorted(raw_names)]
    if isinstance(raw_names, list):
        return [str(value) for value in raw_names]
    raise ValueError("dataset YAML 'names' must be a list or integer-keyed mapping")


def _dataset_root(dataset_yaml: Path, config: dict[str, object]) -> Path:
    raw = str(config.get("path", "."))
    path = Path(raw)
    if path.is_absolute():
        return path
    return (dataset_yaml.parent / path).resolve()


def _labels_dir_from_images(images_dir: Path) -> Path:
    parts = list(images_dir.parts)
    if "images" in parts:
        index = len(parts) - 1 - parts[::-1].index("images")
        parts[index] = "labels"
        return Path(*parts)
    return images_dir.parent / "labels" / images_dir.name


def validate_yolo_dataset(dataset_yaml: Path) -> DatasetReport:
    dataset_yaml = dataset_yaml.resolve()
    config = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("dataset YAML must contain a mapping")
    names = _class_names(config.get("names"))
    root = _dataset_root(dataset_yaml, config)
    split_reports: dict[str, SplitReport] = {}
    hashes: dict[str, list[tuple[str, str]]] = {}

    for split in ("train", "val", "test"):
        raw_dir = config.get(split)
        if not raw_dir:
            continue
        images_dir = (root / str(raw_dir)).resolve()
        labels_dir = _labels_dir_from_images(images_dir)
        report = SplitReport(
            split=split,
            class_counts={name: 0 for name in names},
        )
        images = list_images(images_dir)
        report.image_count = len(images)
        for image_path in images:
            image = cv2.imread(str(image_path))
            if image is not None:
                image_hash = dhash(image)
                hashes.setdefault(image_hash, []).append((split, image_path.name))
            label_path = labels_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                report.missing_labels.append(image_path.name)
                continue
            report.labelled_image_count += 1
            for line_number, raw_line in enumerate(
                label_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not raw_line.strip():
                    continue
                try:
                    values = parse_yolo_line(raw_line)
                except (ValueError, TypeError) as exc:
                    report.invalid_labels.append(
                        LabelIssue(str(label_path), line_number, str(exc))
                    )
                    continue
                issues = validate_yolo_values(values, len(names))
                if issues:
                    report.invalid_labels.append(
                        LabelIssue(str(label_path), line_number, "; ".join(issues))
                    )
                    continue
                class_id = values[0]
                report.class_counts[names[class_id]] += 1
                report.object_count += 1
        split_reports[split] = report

    duplicates: dict[str, list[str]] = {}
    cross_split: dict[str, list[str]] = {}
    for image_hash, entries in hashes.items():
        if len(entries) <= 1:
            continue
        printable = [f"{split}:{filename}" for split, filename in entries]
        duplicates[image_hash] = printable
        if len({split for split, _ in entries}) > 1:
            cross_split[image_hash] = printable

    return DatasetReport(
        dataset_yaml=str(dataset_yaml),
        class_names=names,
        splits=split_reports,
        duplicate_hashes=duplicates,
        cross_split_duplicate_hashes=cross_split,
    )


def class_counts_from_labels(label_files: Iterable[Path], class_names: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in class_names}
    for label_file in label_files:
        for line in label_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            class_id, *_ = parse_yolo_line(line)
            if 0 <= class_id < len(class_names):
                counts[class_names[class_id]] += 1
    return counts
