from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_candidate_selector", ROOT / "scripts" / "analyze_candidate_selector.py")
assert SPEC is not None
selector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(selector)

SEMANTIC_SPEC = importlib.util.spec_from_file_location(
    "make_semantic_judge_requests", ROOT / "scripts" / "make_semantic_judge_requests.py"
)
assert SEMANTIC_SPEC is not None
semantic_requests = importlib.util.module_from_spec(SEMANTIC_SPEC)
assert SEMANTIC_SPEC.loader is not None
SEMANTIC_SPEC.loader.exec_module(semantic_requests)


def test_test_aware_score_penalizes_unsafe_edits() -> None:
    safe = {
        "patch_apply": True,
        "visible_pass": True,
        "selection_compliant": True,
        "submission_compliant": True,
        "patch_files": 1,
        "patch_lines": 20,
        "test_file_edit": False,
        "workdir_drift": False,
        "unsafe_edit": False,
    }
    unsafe = dict(safe, unsafe_edit=True, test_file_edit=True)
    assert selector.test_aware_score(safe) > selector.test_aware_score(unsafe)


def test_semantic_selector_score_uses_root_cause_signal() -> None:
    strong = {
        "semantic_scores": {
            "fixes_root_cause": 5,
            "test_relevance": 5,
            "minimal_and_targeted": 4,
            "risk_of_regression": 1,
        },
        "patch_apply": True,
        "visible_pass": False,
        "selection_compliant": True,
        "submission_compliant": True,
        "patch_files": 1,
        "patch_lines": 80,
    }
    weak = dict(strong, semantic_scores={"fixes_root_cause": 1, "test_relevance": 1, "minimal_and_targeted": 2, "risk_of_regression": 4})
    assert selector.semantic_selector_score(strong) > selector.semantic_selector_score(weak)


def test_pairwise_scores_accumulate_confidence(tmp_path: Path) -> None:
    path = tmp_path / "pairwise.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"task_id": "t1", "candidate_a": 0, "candidate_b": 1, "winner": "A", "confidence": 0.7}),
                json.dumps({"task_id": "t1", "candidate_a": 0, "candidate_b": 2, "winner": "B", "confidence": 0.5}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    scores = selector.load_pairwise_scores(path)
    assert scores[("t1", 0)] == 0.7
    assert scores[("t1", 2)] == 0.5


def test_logistic_training_prefers_successful_feature_pattern() -> None:
    good = {
        "patch_apply": True,
        "visible_pass": True,
        "submission_compliant": True,
        "selection_compliant": True,
        "empty_patch": False,
        "patch_lines": 20,
        "patch_files": 1,
        "eval": {"success": "True"},
    }
    bad = {
        "patch_apply": False,
        "visible_pass": False,
        "submission_compliant": False,
        "selection_compliant": False,
        "empty_patch": True,
        "patch_lines": 300,
        "patch_files": 4,
        "unsafe_edit": True,
        "eval": {"success": "False"},
    }
    weights = selector.train_logistic([good, bad], epochs=80)
    assert selector.predict_probability(weights, selector.feature_vector(good)) > selector.predict_probability(
        weights, selector.feature_vector(bad)
    )


def test_semantic_prompt_contains_required_json_schema() -> None:
    prompt = semantic_requests.semantic_prompt(
        {"issue": "Fix timezone parsing."},
        {"candidate_dir": "missing", "changed_files": ["django/utils/dateparse.py"], "failure_summary": "AssertionError"},
    )
    assert "fixes_root_cause" in prompt
    assert "Candidate patch" in prompt
    assert "Fix timezone parsing." in prompt
