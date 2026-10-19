from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark SyncCart model inference on the actual laptop")
    parser.add_argument("--weights", default="models/weights/synccart-sku-v001.pt")
    parser.add_argument("--images", default="ml/datasets/demo_sku/images/test")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", default="runtime/evaluation/synccart-sku-v001.benchmark.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit('Install Vision ML dependencies with: pip install -e ".\\services\\vision[yolo]"') from exc
    weights = Path(args.weights)
    image_dir = Path(args.images)
    if not weights.exists():
        raise SystemExit(f"Weights not found: {weights}")
    images = [p for p in sorted(image_dir.glob("*")) if p.is_file()][: max(1, args.limit)]
    if not images:
        raise SystemExit(f"No images found in {image_dir}")
    model = YOLO(str(weights))
    latencies = []
    for index, image in enumerate(images):
        started = time.perf_counter()
        model.predict(source=str(image), imgsz=args.imgsz, device=args.device, verbose=False)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if index > 1:
            latencies.append(elapsed_ms)
    if not latencies:
        raise SystemExit("Not enough images to benchmark after warm-up")
    sorted_latencies = sorted(latencies)
    p95 = sorted_latencies[min(len(sorted_latencies) - 1, int(round(0.95 * (len(sorted_latencies) - 1))))]
    mean = statistics.mean(latencies)
    payload = {
        "weights": str(weights.resolve()),
        "device": args.device,
        "images_measured": len(latencies),
        "latency_ms": {
            "mean": round(mean, 3),
            "median": round(statistics.median(latencies), 3),
            "p95": round(p95, 3),
            "min": round(min(latencies), 3),
            "max": round(max(latencies), 3),
        },
        "approx_fps_from_mean": round(1000.0 / mean, 3) if mean > 0 else None,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
