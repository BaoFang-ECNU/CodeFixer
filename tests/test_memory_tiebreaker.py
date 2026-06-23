from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_memory_tiebreaker", ROOT / "scripts" / "analyze_memory_tiebreaker.py")
assert SPEC is not None
memory_tiebreaker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(memory_tiebreaker)


def test_tiebreaker_tau_zero_keeps_top_original_score() -> None:
    candidates = [
        {"candidate_index": 0, "score": 100, "unsafe_edit": True, "patch_lines": 10},
        {"candidate_index": 1, "score": 95, "unsafe_edit": False, "patch_lines": 10},
    ]
    best = memory_tiebreaker.select_with_memory_tiebreaker(
        candidates,
        {"unsafe_edit": 100},
        tau=0,
        epsilon=10,
    )
    assert best["candidate_index"] == 0


def test_tiebreaker_uses_memory_within_tau_window() -> None:
    candidates = [
        {"candidate_index": 0, "score": 100, "unsafe_edit": True, "patch_lines": 10},
        {"candidate_index": 1, "score": 99, "unsafe_edit": False, "patch_lines": 10},
    ]
    best = memory_tiebreaker.select_with_memory_tiebreaker(
        candidates,
        {"unsafe_edit": 100},
        tau=2,
        epsilon=10,
    )
    assert best["candidate_index"] == 1


def test_tiebreaker_respects_original_selector_tiers_before_score() -> None:
    candidates = [
        {
            "candidate_index": 0,
            "score": 999,
            "patch_apply": True,
            "selection_compliant": False,
            "submission_compliant": True,
            "visible_pass": False,
            "workdir_drift": False,
            "patch_lines": 10,
        },
        {
            "candidate_index": 1,
            "score": 100,
            "patch_apply": True,
            "selection_compliant": True,
            "submission_compliant": True,
            "visible_pass": True,
            "workdir_drift": False,
            "patch_lines": 12,
        },
    ]
    best = memory_tiebreaker.select_with_memory_tiebreaker(
        candidates,
        {},
        tau=0,
        epsilon=0,
    )
    assert best["candidate_index"] == 1


def test_tiebreaker_selected_anchor_reproduces_original_choice() -> None:
    candidates = [
        {"candidate_index": 0, "score": 120, "unsafe_edit": False, "patch_lines": 10},
        {"candidate_index": 1, "score": 100, "unsafe_edit": False, "patch_lines": 12},
    ]
    best = memory_tiebreaker.select_with_memory_tiebreaker(
        candidates,
        {},
        tau=0,
        epsilon=0,
        original_candidate_index=1,
    )
    assert best["candidate_index"] == 1


def test_summary_computes_rates() -> None:
    rows = [
        {
            "success": "True",
            "fix_pass": "True",
            "regression_pass": "False",
            "hidden_pass": "True",
            "submission_compliant": "True",
            "unsafe_edit": "False",
            "empty_patch": "False",
            "patch_lines": "10",
            "patch_files": "1",
        },
        {
            "success": "False",
            "fix_pass": "False",
            "regression_pass": "True",
            "hidden_pass": "False",
            "submission_compliant": "False",
            "unsafe_edit": "True",
            "empty_patch": "False",
            "patch_lines": "30",
            "patch_files": "3",
        },
    ]
    summary = memory_tiebreaker.summarize_selection(5, 0.1, rows, [])
    assert summary["pass_at_1"] == 0.5
    assert summary["submission_compliance_rate"] == 0.5
    assert summary["avg_patch_lines"] == 20
