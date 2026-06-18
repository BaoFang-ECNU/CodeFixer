from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codefixer_baseline.paths import outputs_dir, run_dir, runs_dir, summary_dir


def test_output_paths_are_under_project_root() -> None:
    assert outputs_dir(ROOT) == ROOT / "outputs"
    assert runs_dir(ROOT) == ROOT / "outputs" / "runs"
    assert summary_dir(ROOT) == ROOT / "outputs" / "summary"
    assert run_dir("qwen3_lite_single_0", ROOT) == ROOT / "outputs" / "runs" / "qwen3_lite_single_0"
