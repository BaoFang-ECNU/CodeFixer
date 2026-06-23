from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_llm_judge", ROOT / "scripts" / "run_llm_judge.py")
assert SPEC is not None
judge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(judge)


def test_extract_json_object_handles_markdown_wrapper() -> None:
    parsed = judge.extract_json_object('```json\n{"winner":"A","confidence":0.8}\n```')
    assert parsed["winner"] == "A"
    assert parsed["confidence"] == 0.8


def test_semantic_result_clamps_scores() -> None:
    result = judge.semantic_result(
        {"task_id": "t1", "candidate_index": 2},
        {
            "fixes_root_cause": 9,
            "minimal_and_targeted": 4.2,
            "risk_of_regression": -1,
            "test_relevance": "bad",
            "reason": "ok",
        },
        "raw",
    )
    assert result["fixes_root_cause"] == 5
    assert result["minimal_and_targeted"] == 4
    assert result["risk_of_regression"] == 0
    assert result["test_relevance"] == 0


def test_pairwise_result_normalizes_unknown_winner() -> None:
    result = judge.pairwise_result(
        {"task_id": "t1", "candidate_a": 0, "candidate_b": 1},
        {"winner": "C", "confidence": 2.0, "reason": "unclear"},
        "raw",
    )
    assert result["winner"] == "TIE"
    assert result["confidence"] == 1.0


def test_request_key_modes() -> None:
    assert judge.request_key({"task_id": "t", "candidate_index": 1}, "semantic") == ("t", 1)
    assert judge.request_key({"task_id": "t", "candidate_a": 0, "candidate_b": 2}, "pairwise") == ("t", 0, 2)
