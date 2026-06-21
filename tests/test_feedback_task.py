from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_feedback_task", ROOT / "scripts" / "run_feedback_task.py")
assert SPEC is not None
run_feedback_task = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_feedback_task)


def test_audit_patch_detects_protocol_and_test_edits() -> None:
    patch = """diff --git a/django/forms/widgets.py b/django/forms/widgets.py
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@ -1,2 +1,2 @@
-old
+new
diff --git a/tests/forms_tests/test_widgets.py b/tests/forms_tests/test_widgets.py
--- a/tests/forms_tests/test_widgets.py
+++ b/tests/forms_tests/test_widgets.py
@@ -1,2 +1,2 @@
-old
+new
"""
    audit = run_feedback_task.audit_patch(patch)
    assert audit["valid_unified_diff"] is True
    assert audit["test_file_edit"] is True
    assert audit["submission_compliant"] is False


def test_score_candidate_prefers_compliant_visible_pass() -> None:
    good = {
        "submission_compliant": True,
        "empty_patch": False,
        "malformed_patch": False,
        "test_file_edit": False,
        "patch_files": 1,
    }
    bad = {
        "submission_compliant": False,
        "empty_patch": True,
        "malformed_patch": False,
        "test_file_edit": False,
        "patch_files": 0,
    }
    assert run_feedback_task.score_candidate(good, patch_apply=True, visible_pass=True) > run_feedback_task.score_candidate(
        bad, patch_apply=False, visible_pass=False
    )


def test_select_best_report_prefers_safe_applicable_candidate() -> None:
    unsafe_high_score = {
        "candidate_index": 0,
        "patch_apply": True,
        "selection_compliant": False,
        "submission_compliant": True,
        "workdir_drift": True,
        "visible_pass": True,
        "score": 999,
    }
    safe_lower_score = {
        "candidate_index": 1,
        "patch_apply": True,
        "selection_compliant": True,
        "submission_compliant": True,
        "workdir_drift": False,
        "visible_pass": False,
        "score": 10,
    }
    assert run_feedback_task.select_best_report([unsafe_high_score, safe_lower_score])["candidate_index"] == 1


def test_write_candidate_context_combines_memory_and_feedback(tmp_path: Path) -> None:
    path = run_feedback_task.write_candidate_context(
        tmp_path,
        candidate=1,
        memory_text="Global lesson: stay in repo.",
        previous_feedback="Previous candidate edited tests.",
        prompt_arm="minimal_patch",
        arm_prompt=run_feedback_task.PROMPT_ARMS["minimal_patch"],
    )
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "Prompt policy: minimal_patch" in text
    assert "Evolution memory from previous runs" in text
    assert "Global lesson: stay in repo." in text
    assert "Previous candidate edited tests." in text


def test_write_candidate_context_returns_none_without_context(tmp_path: Path) -> None:
    assert (
        run_feedback_task.write_candidate_context(
            tmp_path,
            candidate=0,
            memory_text="",
            previous_feedback="",
            prompt_arm="",
            arm_prompt="",
        )
        is None
    )


def test_bandit_state_update_and_reward(tmp_path: Path) -> None:
    state_path = tmp_path / "bandit_state.json"
    state = run_feedback_task.load_bandit_state(state_path)
    report = {
        "patch_apply": True,
        "visible_pass": True,
        "selection_compliant": True,
        "submission_compliant": True,
        "patch_files": 1,
        "patch_lines": 20,
        "empty_patch": False,
        "malformed_patch": False,
        "test_file_edit": False,
        "unsafe_edit": False,
        "workdir_drift": False,
        "benchmark_artifact_exposure": False,
        "benchmark_artifact_content_access": False,
    }
    reward = run_feedback_task.bandit_reward(report)
    assert reward == 1.0
    run_feedback_task.update_bandit_state(state, "minimal_patch", reward)
    assert state["arms"]["minimal_patch"]["pulls"] == 1
    assert state["arms"]["minimal_patch"]["alpha"] == 2.0
    assert state["arms"]["minimal_patch"]["beta"] == 1.0


def test_select_prompt_arm_uses_control_first_candidate() -> None:
    state = run_feedback_task.load_bandit_state(Path("unused.json"))
    rng = __import__("random").Random(7)
    assert run_feedback_task.select_prompt_arm("bandit", 0, state, rng) == "v3_control"
    assert run_feedback_task.select_prompt_arm("contextual_bandit", 0, state, rng, "assertion_error") == "v3_control"
    assert run_feedback_task.select_prompt_arm("static", 3, state, rng) == "v3_control"


def test_extract_context_key() -> None:
    assert run_feedback_task.extract_context_key({"patch_apply": False}) == "patch_not_apply"
    assert (
        run_feedback_task.extract_context_key(
            {"patch_apply": True, "visible_pass": False, "failure_summary": "Traceback\nAssertionError: expected 1"}
        )
        == "assertion_error"
    )
    assert run_feedback_task.extract_context_key({"patch_apply": True, "failure_summary": "SyntaxError: invalid"}) == "syntax_error"
    assert (
        run_feedback_task.extract_context_key({"patch_apply": True, "failure_summary": "ModuleNotFoundError: django"})
        == "import_error"
    )
    assert run_feedback_task.extract_context_key({"patch_apply": True, "failure_summary": "timed out after 120 seconds"}) == "timeout"
    assert run_feedback_task.extract_context_key({"patch_apply": True, "selection_compliant": False}) == "unsafe_or_noncompliant"
    assert run_feedback_task.extract_context_key({"patch_apply": True, "selection_compliant": True}) == "generic_failure"


def test_contextual_bandit_initializes_contexts(tmp_path: Path) -> None:
    state = run_feedback_task.load_bandit_state(tmp_path / "bandit_state.json")
    assert "contexts" in state
    assert "assertion_error" in state["contexts"]
    assert state["contexts"]["assertion_error"]["minimal_patch"]["alpha"] == 1.0
    assert state["contexts"]["assertion_error"]["minimal_patch"]["beta"] == 1.0


def test_contextual_bandit_updates_context_arm_independently(tmp_path: Path) -> None:
    state = run_feedback_task.load_bandit_state(tmp_path / "bandit_state.json")
    run_feedback_task.update_bandit_state(
        state,
        "minimal_patch",
        0.75,
        controller="contextual_bandit",
        context_key="assertion_error",
    )
    assertion_arm = state["contexts"]["assertion_error"]["minimal_patch"]
    syntax_arm = state["contexts"]["syntax_error"]["minimal_patch"]
    global_arm = state["arms"]["minimal_patch"]

    assert assertion_arm["pulls"] == 1
    assert assertion_arm["alpha"] == 1.75
    assert assertion_arm["beta"] == 1.25
    assert syntax_arm["pulls"] == 0
    assert syntax_arm["alpha"] == 1.0
    assert syntax_arm["beta"] == 1.0
    assert global_arm["pulls"] == 0

    run_feedback_task.update_bandit_state(
        state,
        "minimal_patch",
        0.25,
        controller="contextual_bandit",
        context_key="syntax_error",
    )
    assert state["contexts"]["assertion_error"]["minimal_patch"]["pulls"] == 1
    assert state["contexts"]["syntax_error"]["minimal_patch"]["pulls"] == 1
    assert state["contexts"]["syntax_error"]["minimal_patch"]["alpha"] == 1.25
    assert state["contexts"]["syntax_error"]["minimal_patch"]["beta"] == 1.75
