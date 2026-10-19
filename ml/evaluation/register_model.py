from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register validated SyncCart SKU weights for the Vision runtime")
    parser.add_argument("--weights", required=True, help="Validated best.pt path")
    parser.add_argument("--metrics", required=True, help="Metrics JSON from evaluate_model.py")
    parser.add_argument("--version", default="v001")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights = Path(args.weights)
    metrics_path = Path(args.metrics)
    if not weights.exists() or not metrics_path.exists():
        raise SystemExit("Both --weights and --metrics must exist")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    runtime_weights = Path("models/weights/synccart-sku-v001.pt")
    registry = Path("models/registry/synccart-sku-v001")
    registry.mkdir(parents=True, exist_ok=True)
    if runtime_weights.exists() and not args.force:
        raise SystemExit(f"{runtime_weights} already exists; use --force to replace it")
    runtime_weights.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(weights, runtime_weights)
    shutil.copy2(weights, registry / "model.pt")
    (registry / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    metadata = {
        "model_name": "synccart-sku",
        "model_version": args.version,
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "runtime_weights": str(runtime_weights),
        "source_weights": str(weights.resolve()),
        "evaluation_metrics": str((registry / "metrics.json").resolve()),
    }
    (registry / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    card = f"""# SyncCart SKU Detector {args.version} — Model Card\n\n## Status\n\nRegistered after offline evaluation. Do not describe this model as production-grade without pilot evidence.\n\n## Intended purpose\n\nDetect the controlled MVP SKU classes on the fixed SyncCart demo shelf so the Vision worker can estimate per-zone counts and generate stable pickup/return events.\n\n## Evaluation\n\n- precision: {metrics.get('precision', 'not available')}\n- recall: {metrics.get('recall', 'not available')}\n- mAP50: {metrics.get('map50', 'not available')}\n- mAP50-95: {metrics.get('map50_95', 'not available')}\n- split: {metrics.get('split', 'not available')}\n- device: {metrics.get('device', 'not available')}\n\n## MVP boundaries\n\n- fixed Phone 1 camera;\n- controlled planogram;\n- one SKU family per shelf zone;\n- one active shopper session for safe attribution;\n- no face recognition or demographic inference;\n- stable count-change detection, not hand-action recognition.\n\n## Failure behavior\n\nCamera failure, missing model, ambiguous multi-session state, or low-confidence detections must not create fabricated physical-cart evidence.\n"""
    (registry / "model_card.md").write_text(card, encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
