from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "HACKATHON_SUBMISSION.md",
    "pyproject.toml",
    "package.json",
    ".env.example",
    "services/api/app/main.py",
    "services/vision/synccart_vision/main.py",
    "apps/customer-web/src/App.tsx",
    "apps/retailer-web/src/App.tsx",
    "apps/monitoring-web/src/App.tsx",
    "config/vision_planogram.yaml",
    "ml/datasets/demo_sku/dataset.yaml",
]

FORBIDDEN_NAMES = {".env", "node_modules", ".venv"}
FORBIDDEN_SUFFIXES = {".pt", ".pth", ".onnx", ".db", ".sqlite", ".sqlite3"}
EXPECTED_CLASSES = ["copy", "olive_oil", "bottle"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify SyncCart hackathon source bundle")
    parser.add_argument("--run-tests", action="store_true", help="Run pytest -q after static checks")
    return parser.parse_args()


def source_count() -> int:
    suffixes = {".py", ".ts", ".tsx", ".css", ".html", ".yaml", ".yml", ".toml", ".json"}
    return sum(1 for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in suffixes)


def main() -> int:
    args = parse_args()
    failures: list[str] = []

    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            failures.append(f"missing required path: {relative}")

    for path in ROOT.rglob("*"):
        if any(part in FORBIDDEN_NAMES for part in path.parts):
            failures.append(f"forbidden generated directory/file present: {path.relative_to(ROOT)}")
            continue
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"forbidden generated artifact present: {path.relative_to(ROOT)}")

    planogram_path = ROOT / "config/vision_planogram.yaml"
    if planogram_path.exists():
        planogram = yaml.safe_load(planogram_path.read_text(encoding="utf-8")) or {}
        classes = list((planogram.get("class_to_sku") or {}).keys())
        if classes != EXPECTED_CLASSES:
            failures.append(f"planogram classes are {classes!r}; expected {EXPECTED_CLASSES!r}")

    dataset_path = ROOT / "ml/datasets/demo_sku/dataset.yaml"
    if dataset_path.exists():
        dataset = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or {}
        names = dataset.get("names") or {}
        ordered = [names[key] for key in sorted(names)] if isinstance(names, dict) else list(names)
        if ordered != EXPECTED_CLASSES:
            failures.append(f"dataset classes are {ordered!r}; expected {EXPECTED_CLASSES!r}")

    print("SyncCart submission verification")
    print(f"root: {ROOT}")
    print(f"source/config files counted: {source_count()}")

    if failures:
        print("\nSTATIC CHECK: FAIL")
        for item in failures:
            print(f" - {item}")
        return 1

    print("STATIC CHECK: PASS")

    if args.run_tests:
        print("\nRunning pytest -q ...")
        result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
