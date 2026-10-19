from __future__ import annotations

import argparse
import json
from pathlib import Path

from synccart_vision.dataops import validate_yolo_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SyncCart YOLO dataset integrity")
    parser.add_argument("--data", default="ml/datasets/demo_sku/dataset.yaml")
    parser.add_argument("--output", default="runtime/dataset_validation.json")
    parser.add_argument("--fail-on-invalid", action="store_true")
    return parser.parse_args()


def markdown(report: dict[str, object]) -> str:
    lines = ["# SyncCart Dataset Validation", "", f"Valid: **{report['valid']}**", ""]
    splits = report.get("splits", {})
    if isinstance(splits, dict):
        for name, raw in splits.items():
            if not isinstance(raw, dict):
                continue
            lines.extend(
                [
                    f"## {name}",
                    "",
                    f"- images: {raw.get('image_count', 0)}",
                    f"- labelled images: {raw.get('labelled_image_count', 0)}",
                    f"- objects: {raw.get('object_count', 0)}",
                    f"- missing labels: {len(raw.get('missing_labels', []))}",
                    f"- invalid labels: {len(raw.get('invalid_labels', []))}",
                    "",
                ]
            )
            counts = raw.get("class_counts", {})
            if isinstance(counts, dict):
                lines.append("| Class | Objects |")
                lines.append("|---|---:|")
                for class_name, count in counts.items():
                    lines.append(f"| {class_name} | {count} |")
                lines.append("")
    cross = report.get("cross_split_duplicate_hashes", {})
    lines.append(f"Cross-split exact visual duplicate groups: **{len(cross) if isinstance(cross, dict) else 0}**")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = validate_yolo_dataset(Path(args.data))
    payload = report.to_dict()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path = output.with_suffix(".md")
    md_path.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Saved {output} and {md_path}")
    if args.fail_on_invalid and not report.valid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
