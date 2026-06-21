from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codefixer_baseline.local_eval import analyze_patch, run_shell, summarize_system, write_command_log


def test_analyze_patch_detects_section_63_metrics() -> None:
    patch = """diff --git a/buggy_math.py b/buggy_math.py
--- a/buggy_math.py
+++ b/buggy_math.py
@@ -1,2 +1,2 @@
-def add(a, b):
-    return a - b
+def add(a, b):
+    return a + b
diff --git a/tests/test_visible.py b/tests/test_visible.py
--- a/tests/test_visible.py
+++ b/tests/test_visible.py
@@ -1,2 +1,1 @@
-def test_add():
-    assert add(1, 2) == 3
+# removed
"""
    stats = analyze_patch(patch, relevant_files=("buggy_math.py",))
    assert stats["patch_lines"] == 7
    assert stats["patch_files"] == 2
    assert stats["test_deletion"] is True
    assert stats["unsafe_edit"] is True
    assert stats["irrelevant_file_edits"] == 1


def test_analyze_patch_does_not_treat_source_name_containing_test_as_test_file() -> None:
    patch = """diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py
--- a/astropy/modeling/separable.py
+++ b/astropy/modeling/separable.py
@@ -1,2 +1,2 @@
-old
+new
"""
    stats = analyze_patch(patch, relevant_files=("astropy/modeling/separable.py",))
    assert stats["test_deletion"] is False
    assert stats["unsafe_edit"] is False
    assert stats["irrelevant_file_edits"] == 0


def test_summarize_system_computes_pass_at_k_and_rates() -> None:
    tasks = [
        type("Task", (), {"id": "t1"})(),
        type("Task", (), {"id": "t2"})(),
    ]
    rows = [
        {"system": "baseline", "task_id": "t1", "candidate_index": 0, "success": False, "visible_pass": True, "hidden_pass": False, "tool_calls": 2, "test_runs": 1, "patch_lines": 4, "patch_files": 1, "unsafe_edit": False, "cost": 0, "wall_time_sec": 10},
        {"system": "baseline", "task_id": "t1", "candidate_index": 1, "success": True, "visible_pass": True, "hidden_pass": True, "tool_calls": 3, "test_runs": 2, "patch_lines": 5, "patch_files": 1, "unsafe_edit": False, "cost": 0, "wall_time_sec": 12},
        {"system": "baseline", "task_id": "t2", "candidate_index": 0, "success": True, "visible_pass": True, "hidden_pass": True, "tool_calls": 1, "test_runs": 1, "patch_lines": 2, "patch_files": 1, "unsafe_edit": True, "cost": 0, "wall_time_sec": 8},
    ]
    summary = summarize_system("baseline", tasks, rows)
    assert summary["pass_at_1"] == 0.5
    assert summary["pass_at_k"] == 1.0
    assert summary["visible_test_pass_rate"] == 1.0
    assert summary["hidden_regression_test_pass_rate"] == 0.6667
    assert summary["unsafe_edit_rate"] == 0.3333


def test_write_command_log_records_actual_command_metadata(tmp_path: Path) -> None:
    result = run_shell("python --version", tmp_path, timeout_sec=10)
    write_command_log(tmp_path, "version check", result)

    meta = json.loads((tmp_path / "version_check.meta.json").read_text(encoding="utf-8"))
    assert meta["command"] == "python --version"
    assert meta["cwd"] == str(tmp_path)
    assert meta["timeout_sec"] == 10
    assert isinstance(meta["duration_sec"], float)
    assert (tmp_path / "version_check.stdout.txt").exists()
    assert (tmp_path / "version_check.stderr.txt").exists()
