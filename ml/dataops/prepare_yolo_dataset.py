from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import yaml

DEFAULT_CLASSES = ["copy", "olive_oil", "bottle"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create leakage-resistant YOLO train/val/test splits")
    parser.add_argument("--source", required=True, help="Directory containing images/ and labels/")
    parser.add_argument("--output", default="ml/datasets/demo_sku")
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--val", type=float, default=0.15)
    parser.add_argument("--test", type=float, default=0.15)
    parser.add_argument("--classes", nargs="+", default=DEFAULT_CLASSES)
    parser.add_argument("--clean", action="store_true", help="Clear output images/labels before preparing")
    return parser.parse_args()


def group_key(stem: str) -> str:
    if "__" in stem:
        return stem.split("__", 1)[0]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return stem


def assign_groups(groups: list[str], train: float, val: float, test: float) -> dict[str, str]:
    """Assign whole capture groups to splits using deterministic hash ordering.

    The allocator keeps groups intact and, when at least three groups are available,
    reserves at least one group for validation and test.
    """
    unique_groups = sorted(set(groups), key=lambda group: hashlib.sha256(group.encode("utf-8")).hexdigest())
    count = len(unique_groups)
    if count == 0:
        return {}
    if count == 1:
        return {unique_groups[0]: "train"}
    if count == 2:
        return {unique_groups[0]: "train", unique_groups[1]: "test"}

    val_count = max(1, round(count * val))
    test_count = max(1, round(count * test))
    train_count = count - val_count - test_count
    if train_count < 1:
        overflow = 1 - train_count
        while overflow > 0 and val_count > 1:
            val_count -= 1
            overflow -= 1
        while overflow > 0 and test_count > 1:
            test_count -= 1
            overflow -= 1
        train_count = count - val_count - test_count

    assignments: dict[str, str] = {}
    for index, group in enumerate(unique_groups):
        if index < train_count:
            assignments[group] = "train"
        elif index < train_count + val_count:
            assignments[group] = "val"
        else:
            assignments[group] = "test"
    return assignments


def main() -> None:
    args = parse_args()
    total = args.train + args.val + args.test
    if abs(total - 1.0) > 1e-6:
        raise SystemExit("--train + --val + --test must equal 1.0")
    source = Path(args.source)
    source_images = source / "images"
    source_labels = source / "labels"
    if not source_images.exists() or not source_labels.exists():
        raise SystemExit("Source must contain images/ and labels/ directories")
    output = Path(args.output)
    if args.clean:
        for directory in (output / "images", output / "labels"):
            if directory.exists():
                shutil.rmtree(directory)
    for split in ("train", "val", "test"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    manifest = []
    skipped = []
    image_paths = sorted(path for path in source_images.iterdir() if path.is_file())
    groups = [group_key(path.stem) for path in image_paths]
    assignments = assign_groups(groups, args.train, args.val, args.test)
    for image_path in image_paths:
        label_path = source_labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            skipped.append({"image": image_path.name, "reason": "MISSING_LABEL"})
            continue
        group = group_key(image_path.stem)
        split = assignments[group]
        shutil.copy2(image_path, output / "images" / split / image_path.name)
        shutil.copy2(label_path, output / "labels" / split / label_path.name)
        manifest.append({"image": image_path.name, "group": group, "split": split})

    dataset_yaml = {
        "path": ".",
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(args.classes)},
    }
    (output / "dataset.yaml").write_text(yaml.safe_dump(dataset_yaml, sort_keys=False), encoding="utf-8")
    report = {
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "split_ratios": {"train": args.train, "val": args.val, "test": args.test},
        "prepared": len(manifest),
        "skipped": skipped,
        "manifest": manifest,
    }
    (output / "split_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    counts = {split: sum(1 for item in manifest if item["split"] == split) for split in ("train", "val", "test")}
    print(json.dumps({"prepared": len(manifest), "skipped": len(skipped), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
