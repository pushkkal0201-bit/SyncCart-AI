from __future__ import annotations

import importlib.util
from pathlib import Path


def load_prepare_module():
    path = Path(__file__).parents[3] / "ml" / "dataops" / "prepare_yolo_dataset.py"
    spec = importlib.util.spec_from_file_location("prepare_yolo_dataset", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_group_assignment_preserves_group_and_nonempty_three_way_split() -> None:
    module = load_prepare_module()
    groups = [f"session-{index:02d}" for index in range(1, 8)]
    assignments = module.assign_groups(groups, 0.70, 0.15, 0.15)
    assert set(assignments) == set(groups)
    assert {"train", "val", "test"}.issubset(set(assignments.values()))
    assert assignments == module.assign_groups(groups, 0.70, 0.15, 0.15)
