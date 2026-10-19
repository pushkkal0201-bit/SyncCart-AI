from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained SyncCart YOLO model")
    parser.add_argument("--weights", default="models/weights/synccart-sku-v001.pt")
    parser.add_argument("--data", default="ml/datasets/demo_sku/dataset.yaml")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--output", default="runtime/evaluation/synccart-sku-v001.metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit('Install Vision ML dependencies with: pip install -e ".\\services\\vision[yolo]"') from exc
    weights = Path(args.weights)
    data = Path(args.data)
    if not weights.exists():
        raise SystemExit(f"Weights not found: {weights}")
    if not data.exists():
        raise SystemExit(f"Dataset YAML not found: {data}")

    model = YOLO(str(weights))
    result = model.val(data=str(data.resolve()), split=args.split, device=args.device, imgsz=args.imgsz)
    box = result.box
    payload = {
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "weights": str(weights.resolve()),
        "dataset": str(data.resolve()),
        "split": args.split,
        "device": args.device,
        "imgsz": args.imgsz,
        "precision": float(box.mp),
        "recall": float(box.mr),
        "map50": float(box.map50),
        "map50_95": float(box.map),
        "speed_ms": {key: float(value) for key, value in dict(result.speed).items()},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Saved evaluation metrics to {output}")


if __name__ == "__main__":
    main()
