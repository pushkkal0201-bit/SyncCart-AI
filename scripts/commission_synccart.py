from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "vision"))

from synccart_vision.config import VisionSettings  # noqa: E402
from synccart_vision.planogram import Planogram  # noqa: E402


@dataclass(slots=True)
class Check:
    name: str
    status: str
    detail: str


def http_check(name: str, url: str, *, timeout: float = 2.5) -> Check:
    try:
        response = httpx.get(url, timeout=timeout)
        if response.is_success:
            return Check(name, "PASS", f"{response.status_code} {url}")
        return Check(name, "FAIL", f"HTTP {response.status_code} from {url}")
    except Exception as exc:
        return Check(name, "FAIL", f"{url}: {exc}")


def camera_check(source: str, frames: int = 12) -> Check:
    source_value: int | str = int(source) if source.strip().isdigit() else source
    capture = cv2.VideoCapture(source_value)
    if not capture.isOpened():
        capture.release()
        return Check("camera_source", "FAIL", f"Unable to open camera source {source!r}")
    started = time.perf_counter()
    read = 0
    width = height = 0
    try:
        while read < frames:
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            read += 1
            height, width = frame.shape[:2]
    finally:
        capture.release()
    elapsed = max(time.perf_counter() - started, 1e-6)
    if read < max(3, frames // 2):
        return Check("camera_source", "FAIL", f"Only {read}/{frames} frames could be read")
    return Check(
        "camera_source",
        "PASS",
        f"Read {read} frames at ~{read / elapsed:.1f} FPS, resolution {width}x{height}",
    )


def write_reports(checks: list[Check], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_epoch": time.time(),
        "summary": {
            "pass": sum(c.status == "PASS" for c in checks),
            "warn": sum(c.status == "WARN" for c in checks),
            "fail": sum(c.status == "FAIL" for c in checks),
        },
        "checks": [asdict(c) for c in checks],
    }
    output.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# SyncCart Phase 7 Commissioning Report", ""]
    lines += [f"- PASS: {payload['summary']['pass']}", f"- WARN: {payload['summary']['warn']}", f"- FAIL: {payload['summary']['fail']}", ""]
    for check in checks:
        lines.append(f"## {check.status} — {check.name}")
        lines.append(check.detail)
        lines.append("")
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Commission SyncCart hardware and local services before a live demo")
    parser.add_argument("--core", default="http://127.0.0.1:8000")
    parser.add_argument("--vision", default="http://127.0.0.1:8100")
    parser.add_argument("--customer", default="http://127.0.0.1:5173")
    parser.add_argument("--retailer", default="http://127.0.0.1:5174")
    parser.add_argument("--monitoring", default="http://127.0.0.1:5175")
    parser.add_argument("--camera-source", default=None)
    parser.add_argument("--require-model", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "runtime" / "phase7_commissioning"))
    args = parser.parse_args()

    settings = VisionSettings()
    source = args.camera_source or settings.camera_source
    checks: list[Check] = []

    env_path = ROOT / ".env"
    checks.append(Check("environment_file", "PASS" if env_path.exists() else "WARN", str(env_path) if env_path.exists() else ".env missing; copy .env.example before runtime"))

    try:
        planogram = Planogram.load(settings.planogram_path)
        checks.append(Check("planogram", "PASS", f"{len(planogram.zones)} zones loaded from {settings.planogram_path}"))
    except Exception as exc:
        checks.append(Check("planogram", "FAIL", str(exc)))

    model_exists = settings.yolo_weights.exists() and settings.yolo_weights.stat().st_size > 0
    model_status = "PASS" if model_exists else ("FAIL" if args.require_model else "WARN")
    checks.append(Check("sku_model", model_status, str(settings.yolo_weights) if model_exists else f"Custom weights missing: {settings.yolo_weights}"))

    checks.append(http_check("core_api", f"{args.core.rstrip('/')}/health/ready"))
    checks.append(http_check("vision_service", f"{args.vision.rstrip('/')}/health/ready"))
    checks.append(http_check("customer_app", args.customer))
    checks.append(http_check("retailer_app", args.retailer))
    checks.append(http_check("monitoring_app", args.monitoring))
    checks.append(camera_check(source))

    try:
        response = httpx.get(f"{args.vision.rstrip('/')}/control/status", timeout=2.5)
        if response.is_success:
            state = response.json()
            checks.append(Check("vision_event_gate", "PASS", f"armed={state.get('event_emission_armed')} baseline={state.get('baseline_status')} counts={state.get('zone_counts')}"))
        else:
            checks.append(Check("vision_event_gate", "FAIL", f"HTTP {response.status_code}"))
    except Exception as exc:
        checks.append(Check("vision_event_gate", "FAIL", str(exc)))

    output = Path(args.output)
    write_reports(checks, output)
    for check in checks:
        print(f"[{check.status:4}] {check.name:22} {check.detail}")
    print(f"Reports: {output.with_suffix('.json')} and {output.with_suffix('.md')}")

    failures = sum(c.status == "FAIL" for c in checks)
    warnings = sum(c.status == "WARN" for c in checks)
    if failures or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
