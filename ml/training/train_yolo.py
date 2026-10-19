from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the SyncCart custom SKU detector")
    parser.add_argument("--data", default="ml/datasets/demo_sku/dataset.yaml")
    parser.add_argument("--base-model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--project", default="runtime/training")
    parser.add_argument("--name", default="synccart-sku-v001")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            'Ultralytics is required. Install with: pip install -e ".\\services\\vision[yolo]"'
        ) from exc

    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise SystemExit(f"Dataset YAML not found: {data_path}")

    model = YOLO(args.base_model)
    result = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        seed=args.seed,
        deterministic=True,
        patience=args.patience,
        project=args.project,
        name=args.name,
        exist_ok=False,
        plots=True,
    )
    print(result)
    print("Training complete. Evaluate best.pt on the held-out test split before registration.")


if __name__ == "__main__":
    main()
