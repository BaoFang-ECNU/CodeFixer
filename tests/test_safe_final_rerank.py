from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("safe_final_rerank", ROOT / "scripts" / "safe_final_rerank.py")
assert SPEC is not None
safe_final_rerank = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(safe_final_rerank)


def test_load_memory_counts_parses_failure_section(tmp_path: Path) -> None:
    memory = tmp_path / "memory.md"
    memory.write_text(
        """Evolution memory.

Frequent failure modes to avoid:
- workdir_drift: 53
- unsafe_edit: 36
- test_file_edit: 22

Operational rules:
- stay safe
""",
        encoding="utf-8",
    )
    assert safe_final_rerank.load_memory_counts(memory) == {
        "workdir_drift": 53,
        "unsafe_edit": 36,
        "test_file_edit": 22,
    }


def test_memory_penalties_are_log_scaled() -> None:
    row = {
        "workdir_drift": True,
        "unsafe_edit": True,
        "patch_apply": True,
        "visible_pass": True,
        "patch_lines": 20,
        "patch_files": 1,
    }
    penalties = safe_final_rerank.memory_penalties(row, {"workdir_drift": 53, "unsafe_edit": 1}, 2.0)
    assert penalties["workdir_drift"] > penalties["unsafe_edit"]
    assert penalties["unsafe_edit"] > 0


def test_hard_rule_violations_detects_memory_rules() -> None:
    row = {
        "test_file_edit": False,
        "artifact_file_edit": False,
        "benchmark_artifact_content_access": False,
        "changed_files": ["manage.py", "test_app/models.py", "django/db/models/base.py.orig"],
    }
    violations = safe_final_rerank.hard_rule_violations(row)
    assert "forbidden_file:manage.py" in violations
    assert "reproduction_artifact:test_app/models.py" in violations
    assert "backup_artifact:django/db/models/base.py.orig" in violations


def test_select_memory_safe_candidate_prefers_feasible_candidate() -> None:
    unsafe_visible_pass = {
        "candidate_index": 0,
        "candidate_dir": "unused0",
        "patch_apply": True,
        "visible_pass": True,
        "submission_compliant": True,
        "selection_compliant": False,
        "test_file_edit": True,
        "changed_files": ["tests/test_bug.py"],
        "empty_patch": False,
        "malformed_patch": False,
        "patch_lines": 10,
        "patch_files": 1,
    }
    safe_apply = {
        "candidate_index": 1,
        "candidate_dir": "unused1",
        "patch_apply": True,
        "visible_pass": False,
        "submission_compliant": True,
        "selection_compliant": True,
        "test_file_edit": False,
        "changed_files": ["django/db/models/base.py"],
        "empty_patch": False,
        "malformed_patch": False,
        "patch_lines": 80,
        "patch_files": 1,
    }
    best = safe_final_rerank.select_memory_safe_candidate(
        [unsafe_visible_pass, safe_apply],
        {"test_file_edit": 22, "visible_failed": 5},
    )
    assert best["candidate_index"] == 1
    assert best["hard_rule_violations"] == []
