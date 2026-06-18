from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codefixer_baseline.summarize import NA, SUMMARY_FIELDS, normalize_summary_row, summarize_run, write_summary


def test_normalize_summary_row_fills_missing_fields() -> None:
    row = normalize_summary_row({"run_name": "demo"})
    assert set(row) == set(SUMMARY_FIELDS)
    assert row["run_name"] == "demo"
    assert row["num_instances"] == NA


def test_summarize_run_handles_missing_optional_fields(tmp_path: Path) -> None:
    run_dir = tmp_path / "qwen3_lite_test_0_1"
    run_dir.mkdir()
    (run_dir / "preds.json").write_text(json.dumps([{"instance_id": "x"}]), encoding="utf-8")

    row = summarize_run(run_dir)
    assert row["run_name"] == "qwen3_lite_test_0_1"
    assert row["num_instances"] == 1
    assert row["avg_steps"] == NA
    assert row["resolved_rate"] == NA


def test_write_summary_outputs_csv_and_markdown(tmp_path: Path) -> None:
    csv_path, md_path = write_summary([{"run_name": "demo"}], tmp_path)
    assert csv_path.exists()
    assert md_path.exists()
    assert "demo" in md_path.read_text(encoding="utf-8")
