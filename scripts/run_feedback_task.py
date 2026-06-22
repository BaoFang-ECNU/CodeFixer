#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from codefixer_baseline.local_eval import analyze_agent_artifacts, analyze_patch


VALID_DIFF_HEADER = re.compile(r"^diff --git a/.+ b/.+$", re.M)


PROMPT_ARMS: dict[str, str] = {
    "v3_control": """Prompt policy: v3_control.
Use the standard repair process. Keep the patch source-only, minimal, and valid.""",
    "localization_first": """Prompt policy: localization_first.
First identify the real source file and smallest relevant function before editing.
Avoid broad repository scans, temporary projects, copied checkouts, or scratch files.
Prefer `rg` and small `sed -n` ranges. Edit only the real source file that owns the bug.""",
    "failing_test_first": """Prompt policy: failing_test_first.
Prioritize the visible failure signal. Map the failing behavior to the smallest source change.
Run the most relevant available test after editing. Do not add or edit tests.""",
    "minimal_patch": """Prompt policy: minimal_patch.
Optimize for the smallest correct patch. Prefer one source file and a few lines.
Do not create reproduction files, settings.py, manage.py, test_app/, .fixed files, backups, or test files.
If a fix requires broad edits, re-check whether a narrower source-level change exists.""",
    "regression_conservative": """Prompt policy: regression_conservative.
Preserve existing public behavior and compatibility. Avoid special-casing benchmark inputs.
Before finalizing, reason about likely regression tests and keep the implementation general.""",
    "traceback_api_contract": """Prompt policy: traceback_api_contract.
For Django API, serializer, model field, URL, migration, and traceback-like bugs, locate the contract boundary.
Fix the contract in framework source code rather than patching symptoms in tests or examples.""",
}

DEFAULT_BANDIT_ARMS = [
    "localization_first",
    "failing_test_first",
    "minimal_patch",
    "regression_conservative",
    "traceback_api_contract",
]

DEFAULT_CONTEXT_KEYS = [
    "generic_failure",
    "patch_not_apply",
    "assertion_error",
    "syntax_error",
    "import_error",
    "timeout",
    "unsafe_or_noncompliant",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local +feedback code repair task.")
    parser.add_argument("task_id")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--candidate-system", default="feedback_candidates")
    parser.add_argument("--selected-system", default="feedback")
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--model", default="hosted_vllm/qwen3-coder-30b-a3b")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--step-limit", type=int, default=1000)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--rerank-only", action="store_true", help="Reuse existing candidate patches and only redo selection.")
    parser.add_argument("--memory-file", default="", help="Optional evolution memory to prepend to every candidate prompt.")
    parser.add_argument(
        "--prompt-controller",
        choices=["static", "bandit", "contextual_bandit", "hierarchical_bandit"],
        default="static",
        help=(
            "Prompt policy controller. 'bandit' uses global Thompson sampling; "
            "'contextual_bandit' conditions Thompson sampling on the previous failure type; "
            "'hierarchical_bandit' smooths context-local posteriors with global arm posteriors."
        ),
    )
    parser.add_argument(
        "--bandit-state",
        default="",
        help="Optional JSON state path for bandit arm statistics. Defaults to <feedback-root>/bandit_state.json.",
    )
    parser.add_argument("--bandit-seed", type=int, default=0, help="Random seed for Thompson sampling.")
    parser.add_argument("--hier-tau", type=float, default=3.0, help="Shared-prior smoothing strength for hierarchical_bandit.")
    parser.add_argument(
        "--feedback-root",
        default=str(PROJECT_ROOT / "outputs" / "feedback"),
        help="Directory for per-task feedback reports and feedback prompts.",
    )
    args = parser.parse_args()

    task = load_task(Path(args.manifest), args.task_id)
    feedback_dir = resolve_path(args.feedback_root) / args.task_id
    feedback_dir.mkdir(parents=True, exist_ok=True)
    memory_text = load_memory(args.memory_file)
    bandit_state_path = get_bandit_state_path(args)
    bandit_state = load_bandit_state(bandit_state_path, args.hier_tau) if is_bandit_controller(args.prompt_controller) else None
    rng = random.Random(args.bandit_seed + stable_int(args.task_id))

    reports: list[dict[str, Any]] = []
    bandit_events: list[dict[str, Any]] = []
    previous_feedback = ""
    context_key = "generic_failure"
    for candidate in range(args.attempts):
        arm_name = select_prompt_arm(args.prompt_controller, candidate, bandit_state, rng, context_key)
        arm_prompt = PROMPT_ARMS[arm_name]
        print(f"[feedback-task] {args.task_id} candidate_{candidate}", flush=True)
        print(f"[feedback-task] prompt_arm={arm_name}", flush=True)
        if args.prompt_controller in {"contextual_bandit", "hierarchical_bandit"}:
            print(f"[feedback-task] context_key={context_key}", flush=True)
        candidate_dir = (
            PROJECT_ROOT
            / "outputs"
            / "local_runs"
            / args.candidate_system
            / args.task_id
            / f"candidate_{candidate}"
        )
        if args.rerank_only:
            if not (candidate_dir / "patch.diff").exists():
                print(f"[feedback-task] skip missing existing candidate_{candidate}", flush=True)
                continue
            run_returncode = "rerank_only"
        else:
            context_path = write_candidate_context(feedback_dir, candidate, memory_text, previous_feedback, arm_name, arm_prompt)
            run_result = run_candidate(args, candidate, context_path)
            run_returncode = run_result.returncode
        report = evaluate_candidate_patch(task, candidate_dir, candidate)
        report["agent_returncode"] = run_returncode
        report["prompt_arm"] = arm_name
        report["context_key"] = context_key
        reports.append(report)

        if not args.rerank_only:
            if is_bandit_controller(args.prompt_controller) and bandit_state is not None:
                reward = bandit_reward(report)
                update_bandit_state(bandit_state, arm_name, reward, args.prompt_controller, context_key)
                bandit_state["hier_config"]["tau"] = args.hier_tau
                save_bandit_state(bandit_state_path, bandit_state)
                bandit_events.append(
                    {
                        "candidate_index": candidate,
                        "prompt_arm": arm_name,
                        "context_key": context_key,
                        "reward": reward,
                        "score": report["score"],
                        "patch_apply": report["patch_apply"],
                        "visible_pass": report["visible_pass"],
                        "selection_compliant": report.get("selection_compliant"),
                        "hier_tau": args.hier_tau if args.prompt_controller == "hierarchical_bandit" else "",
                        "context_count": get_context_count(bandit_state, context_key),
                    }
                )
            previous_feedback = build_feedback(task, report)
            context_key = extract_context_key(report)
            feedback_path = feedback_dir / f"feedback_after_candidate_{candidate}.txt"
            feedback_path.write_text(previous_feedback, encoding="utf-8")
        if not args.rerank_only and report["patch_apply"] and report["selection_compliant"] and report["visible_pass"] is True:
            print(f"[feedback-task] early stop: candidate_{candidate} passes visible checks", flush=True)
            break

    if not reports:
        raise SystemExit(f"No candidate patches found for {args.task_id}")

    best = select_best_report(reports)
    selected_dir = (
        PROJECT_ROOT
        / "outputs"
        / "local_runs"
        / args.selected_system
        / args.task_id
        / "candidate_0"
    )
    copy_selected_candidate(best["candidate_dir"], selected_dir)
    write_selected_metadata(selected_dir, args, best, reports)

    report_path = feedback_dir / "feedback_report.json"
    report_path.write_text(
        json.dumps(
            {
                "task_id": args.task_id,
                "memory_file": args.memory_file,
                "memory_chars": len(memory_text),
                "prompt_controller": args.prompt_controller,
                "hier_tau": args.hier_tau if args.prompt_controller == "hierarchical_bandit" else "",
                "bandit_state": str(bandit_state_path) if bandit_state_path else "",
                "bandit_events": bandit_events,
                "best": best,
                "candidates": reports,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[feedback-task] selected candidate_{best['candidate_index']} score={best['score']}")
    print(f"[feedback-task] selected_dir={selected_dir}")
    print(f"[feedback-task] report={report_path}")
    return 0


def load_memory(memory_file: str) -> str:
    if not memory_file:
        return ""
    path = Path(memory_file)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    if not path.exists():
        raise SystemExit(f"Memory file not found: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def write_candidate_context(
    feedback_dir: Path,
    candidate: int,
    memory_text: str,
    previous_feedback: str,
    prompt_arm: str = "v3_control",
    arm_prompt: str = "",
) -> Path | None:
    sections: list[str] = []
    arm_text = arm_prompt or PROMPT_ARMS.get(prompt_arm, "")
    if arm_text:
        sections.append(arm_text)
    if memory_text:
        sections.append("Evolution memory from previous runs:\n" + memory_text)
    if previous_feedback.strip():
        sections.append(previous_feedback.strip())
    if not sections:
        return None
    context_path = feedback_dir / f"context_before_candidate_{candidate}.txt"
    context_path.write_text("\n\n".join(sections).strip() + "\n", encoding="utf-8")
    return context_path


def get_bandit_state_path(args: argparse.Namespace) -> Path:
    if args.bandit_state:
        return resolve_path(args.bandit_state)
    return resolve_path(args.feedback_root) / "bandit_state.json"


def is_bandit_controller(controller: str) -> bool:
    return controller in {"bandit", "contextual_bandit", "hierarchical_bandit"}


def load_bandit_state(path: Path, hier_tau: float = 3.0) -> dict[str, Any]:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {}
    initialize_arm_table(state.setdefault("arms", {}))
    contexts = state.setdefault("contexts", {})
    for context_key in DEFAULT_CONTEXT_KEYS:
        initialize_arm_table(contexts.setdefault(context_key, {}))
    state.setdefault("context_counts", {})
    hier_config = state.setdefault("hier_config", {})
    hier_config.setdefault("mode", "shared_prior")
    hier_config["tau"] = float(hier_tau)
    return state


def initialize_arm_table(arms: dict[str, Any]) -> None:
    for name in ["v3_control", *DEFAULT_BANDIT_ARMS]:
        arm = arms.setdefault(name, {})
        arm.setdefault("alpha", 1.0)
        arm.setdefault("beta", 1.0)
        arm.setdefault("pulls", 0)
        arm.setdefault("reward_sum", 0.0)


def get_context_arms(state: dict[str, Any], context_key: str) -> dict[str, Any]:
    contexts = state.setdefault("contexts", {})
    arms = contexts.setdefault(context_key, {})
    initialize_arm_table(arms)
    return arms


def get_context_count(state: dict[str, Any], context_key: str) -> int:
    return int(state.setdefault("context_counts", {}).get(context_key, 0))


def context_lambda(state: dict[str, Any], context_key: str, tau: float | None = None) -> float:
    if tau is None:
        tau = float(state.setdefault("hier_config", {}).get("tau", 3.0))
    n_context = get_context_count(state, context_key)
    return float(tau) / (float(tau) + n_context)


def save_bandit_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_int(text: str) -> int:
    value = 0
    for char in text:
        value = (value * 131 + ord(char)) % 1_000_000_007
    return value


def select_prompt_arm(
    controller: str,
    candidate: int,
    bandit_state: dict[str, Any] | None,
    rng: random.Random,
    context_key: str = "generic_failure",
) -> str:
    if not is_bandit_controller(controller):
        return "v3_control"
    if candidate == 0:
        return "v3_control"
    assert bandit_state is not None
    if controller == "contextual_bandit":
        arms = get_context_arms(bandit_state, context_key)
    elif controller == "hierarchical_bandit":
        arms = effective_hierarchical_arms(bandit_state, context_key)
    else:
        arms = bandit_state["arms"]
    samples = []
    for name in DEFAULT_BANDIT_ARMS:
        arm = arms[name]
        samples.append((rng.betavariate(float(arm["alpha"]), float(arm["beta"])), name))
    return max(samples, key=lambda item: item[0])[1]


def effective_hierarchical_arms(state: dict[str, Any], context_key: str) -> dict[str, dict[str, float]]:
    local_arms = get_context_arms(state, context_key)
    global_arms = state["arms"]
    lam = context_lambda(state, context_key)
    effective: dict[str, dict[str, float]] = {}
    for name in DEFAULT_BANDIT_ARMS:
        local = local_arms[name]
        glob = global_arms[name]
        effective[name] = {
            "alpha": float(local["alpha"]) + lam * float(glob["alpha"]),
            "beta": float(local["beta"]) + lam * float(glob["beta"]),
        }
    return effective


def update_bandit_state(
    state: dict[str, Any],
    arm_name: str,
    reward: float,
    controller: str = "bandit",
    context_key: str = "generic_failure",
) -> None:
    reward = max(0.0, min(1.0, float(reward)))
    if controller == "contextual_bandit":
        arm = get_context_arms(state, context_key)[arm_name]
        update_arm_counts(arm, reward)
    elif controller == "hierarchical_bandit":
        local_arm = get_context_arms(state, context_key)[arm_name]
        global_arm = state["arms"][arm_name]
        update_arm_counts(local_arm, reward)
        update_arm_counts(global_arm, reward)
        counts = state.setdefault("context_counts", {})
        counts[context_key] = int(counts.get(context_key, 0)) + 1
    else:
        arm = state["arms"][arm_name]
        update_arm_counts(arm, reward)


def update_arm_counts(arm: dict[str, Any], reward: float) -> None:
    arm["alpha"] = round(float(arm["alpha"]) + reward, 6)
    arm["beta"] = round(float(arm["beta"]) + 1.0 - reward, 6)
    arm["pulls"] = int(arm["pulls"]) + 1
    arm["reward_sum"] = round(float(arm["reward_sum"]) + reward, 6)


def extract_context_key(report: dict[str, Any]) -> str:
    failure_summary = str(report.get("failure_summary") or "")
    if report.get("patch_apply") is False:
        return "patch_not_apply"
    if report.get("visible_pass") is False and "AssertionError" in failure_summary:
        return "assertion_error"
    if "SyntaxError" in failure_summary:
        return "syntax_error"
    if "ImportError" in failure_summary or "ModuleNotFoundError" in failure_summary:
        return "import_error"
    if "Timeout" in failure_summary or "timed out" in failure_summary:
        return "timeout"
    if report.get("selection_compliant") is False:
        return "unsafe_or_noncompliant"
    return "generic_failure"


def bandit_reward(report: dict[str, Any]) -> float:
    reward = 0.0
    reward += 0.30 if report.get("patch_apply") else 0.0
    reward += 0.25 if report.get("visible_pass") is True else 0.0
    reward += 0.20 if report.get("selection_compliant") else 0.0
    reward += 0.15 if report.get("submission_compliant") else 0.0
    reward += 0.05 if report.get("patch_files", 99) <= 2 else 0.0
    reward += 0.05 if int(report.get("patch_lines", 9999)) <= 180 else 0.0
    reward -= 0.15 if report.get("empty_patch") else 0.0
    reward -= 0.12 if report.get("malformed_patch") else 0.0
    reward -= 0.20 if report.get("test_file_edit") else 0.0
    reward -= 0.20 if report.get("unsafe_edit") else 0.0
    reward -= 0.18 if report.get("workdir_drift") else 0.0
    reward -= 0.20 if report.get("benchmark_artifact_exposure") else 0.0
    reward -= 0.25 if report.get("benchmark_artifact_content_access") else 0.0
    return round(max(0.0, min(1.0, reward)), 4)


def load_task(manifest: Path, task_id: str) -> dict[str, Any]:
    with manifest.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    for task in data.get("tasks", []):
        if str(task.get("id")) == task_id:
            return task
    raise SystemExit(f"Task not found in manifest: {task_id}")


def run_candidate(args: argparse.Namespace, candidate: int, feedback_path: Path | None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_local_task.py"),
        args.task_id,
        "--manifest",
        args.manifest,
        "--system",
        args.candidate_system,
        "--candidate",
        str(candidate),
        "--model",
        args.model,
        "--step-limit",
        str(args.step_limit),
        "--timeout-sec",
        str(args.timeout_sec),
        "--max-tokens",
        str(args.max_tokens),
    ]
    if feedback_path:
        cmd.extend(["--feedback-file", str(feedback_path)])
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), text=True)


def evaluate_candidate_patch(task: dict[str, Any], candidate_dir: Path, candidate_index: int) -> dict[str, Any]:
    start = time.monotonic()
    patch_path = candidate_dir / "patch.diff"
    patch_text = patch_path.read_text(encoding="utf-8", errors="ignore") if patch_path.exists() else ""
    audit = audit_patch(patch_text)
    eval_patch_stats = analyze_patch(patch_text, tuple(str(x) for x in task.get("relevant_files", [])))
    log_audit = analyze_agent_artifacts(candidate_dir)
    audit.update(
        {
            "patch_lines": eval_patch_stats["patch_lines"],
            "unsafe_edit": eval_patch_stats["unsafe_edit"],
            "irrelevant_file_edits": eval_patch_stats["irrelevant_file_edits"],
            "workdir_drift": log_audit["workdir_drift"],
            "benchmark_artifact_exposure": log_audit["benchmark_artifact_exposure"],
            "benchmark_artifact_content_access": log_audit["benchmark_artifact_content_access"],
        }
    )
    audit["selection_compliant"] = (
        audit["submission_compliant"]
        and not audit["unsafe_edit"]
        and not audit["workdir_drift"]
        and not audit["benchmark_artifact_content_access"]
        and audit["patch_lines"] <= 300
        and audit["patch_files"] <= 5
    )
    patch_apply = False
    visible_pass: bool | str = "NA"
    failure_summary = ""

    repo = resolve_path(task["repo_path"])
    with tempfile.TemporaryDirectory(prefix=f"codefixer-feedback-{task['id']}-") as tmp:
        worktree = Path(tmp) / "repo"
        shutil.copytree(repo, worktree)
        clean = clean_worktree(worktree, str(task.get("base_commit", "")))
        if clean.returncode != 0:
            failure_summary = summarize_output(clean.stdout, clean.stderr)
        else:
            apply = run(["git", "apply", "--whitespace=nowarn", str(patch_path)], cwd=worktree, timeout=60)
            patch_apply = apply.returncode == 0
            if not patch_apply:
                failure_summary = summarize_output(apply.stdout, apply.stderr)
            elif task.get("visible_test_command"):
                visible = run_shell(str(task["visible_test_command"]), cwd=worktree, timeout=int(task.get("timeout_sec", 120)))
                visible_pass = visible.returncode == 0
                if not visible_pass:
                    failure_summary = summarize_output(visible.stdout, visible.stderr)

    score = score_candidate(audit, patch_apply, visible_pass)
    return {
        "candidate_index": candidate_index,
        "candidate_dir": str(candidate_dir),
        "patch_chars": len(patch_text),
        "patch_apply": patch_apply,
        "visible_pass": visible_pass,
        "score": score,
        "failure_summary": failure_summary,
        "duration_sec": round(time.monotonic() - start, 4),
        **audit,
    }


def audit_patch(patch: str) -> dict[str, Any]:
    files = changed_files(patch)
    empty = not bool(patch.strip())
    malformed = (not empty) and not bool(VALID_DIFF_HEADER.search(patch))
    test_file_edit = any(is_test_file(path) for path in files)
    artifact_file_edit = any(is_artifact_file(path) for path in files)
    valid_unified_diff = (not empty) and (not malformed)
    submission_compliant = valid_unified_diff and not test_file_edit and not artifact_file_edit
    return {
        "empty_patch": empty,
        "malformed_patch": malformed,
        "valid_unified_diff": valid_unified_diff,
        "test_file_edit": test_file_edit,
        "artifact_file_edit": artifact_file_edit,
        "submission_compliant": submission_compliant,
        "patch_files": len(files),
        "changed_files": files,
    }


def changed_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[2].startswith("a/") and parts[3].startswith("b/"):
            files.append(parts[3][2:])
    return sorted(set(files))


def is_test_file(path: str) -> bool:
    posix = Path(path).as_posix().lower()
    parts = posix.split("/")
    name = parts[-1] if parts else posix
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py") or name in {"conftest.py", "pytest.ini", "tox.ini"}


def is_artifact_file(path: str) -> bool:
    posix = Path(path).as_posix().lower()
    name = Path(posix).name
    return (
        name in {"record.json", "reference.patch", "hidden_test.patch"}
        or name.startswith("reproduce")
        or name.endswith((".bak", ".backup", ".orig", ".tmp"))
    )


def score_candidate(audit: dict[str, Any], patch_apply: bool, visible_pass: bool | str) -> float:
    score = 0.0
    score += 40 if patch_apply else -80
    score += 25 if audit["submission_compliant"] else -35
    score += 35 if audit.get("selection_compliant") else -60
    score += -30 if audit["empty_patch"] else 5
    score += -25 if audit["malformed_patch"] else 5
    score += -40 if audit["test_file_edit"] else 5
    score += -50 if audit.get("unsafe_edit") else 5
    score += -45 if audit.get("workdir_drift") else 5
    score += -45 if audit.get("benchmark_artifact_content_access") else 0
    score += -25 if audit.get("benchmark_artifact_exposure") else 0
    if visible_pass is True:
        score += 60
    elif visible_pass is False:
        score -= 45
    score -= min(10, audit["patch_files"])
    score -= min(50, max(0, int(audit.get("patch_lines", 0)) - 120) / 10)
    return round(score, 4)


def select_best_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Prefer candidates that are both applicable and safe to submit."""
    tiers = [
        [row for row in reports if row["patch_apply"] and row.get("selection_compliant") and row["visible_pass"] is True],
        [row for row in reports if row["patch_apply"] and row.get("selection_compliant")],
        [row for row in reports if row["patch_apply"] and row.get("submission_compliant") and not row.get("workdir_drift")],
        [row for row in reports if row["patch_apply"] and row.get("submission_compliant")],
        reports,
    ]
    for tier in tiers:
        if tier:
            return max(tier, key=lambda row: row["score"])
    raise ValueError("No reports to select from")


def build_feedback(task: dict[str, Any], report: dict[str, Any]) -> str:
    issues: list[str] = []
    if report["empty_patch"]:
        issues.append("The previous candidate produced an empty patch.")
    if report["malformed_patch"]:
        issues.append("The previous candidate patch was not a valid unified git diff.")
    if report["test_file_edit"]:
        issues.append("The previous candidate edited tests or test configuration; produce a source-only patch.")
    if report["artifact_file_edit"]:
        issues.append("The previous candidate edited benchmark or temporary artifacts; remove those edits.")
    if report.get("workdir_drift"):
        issues.append("The previous candidate used or copied files outside the task repository; stay in the provided repository.")
    if report.get("benchmark_artifact_exposure"):
        issues.append("The previous candidate exposed benchmark artifacts in its trajectory; do not inspect record/reference/hidden-test files.")
    if report.get("patch_lines", 0) > 300:
        issues.append("The previous patch was too large; make the next patch minimal.")
    if not report["patch_apply"]:
        issues.append("The previous candidate patch did not apply cleanly to the base repository.")
    if report["visible_pass"] is False:
        issues.append("The visible test command failed after applying the previous patch.")
    if not issues:
        issues.append("The previous candidate passed the available checks. Keep the patch minimal and source-only.")

    visible = task.get("visible_test_command") or "No visible test command is available."
    files = ", ".join(report["changed_files"]) if report["changed_files"] else "none"
    summary = report.get("failure_summary") or "No failure output was captured."
    issue_text = "\n".join(f"  - {item}" for item in issues)
    return f"""Previous candidate feedback:
- Changed files: {files}
- Patch apply: {report['patch_apply']}
- Visible test command: {visible}
- Visible pass: {report['visible_pass']}
- Patch lines: {report.get('patch_lines', 'NA')}
- Workdir drift: {report.get('workdir_drift', 'NA')}
- Benchmark artifact exposure: {report.get('benchmark_artifact_exposure', 'NA')}
- Selection compliant: {report.get('selection_compliant', 'NA')}
- Compliance issues:
{issue_text}

Failure summary:
{summary}

Next attempt requirements:
- Fix the original issue, not the tests.
- Modify only source files required by the bug fix.
- Stay in the provided repository. Do not clone, copy, or work from `/tmp` or another checkout.
- The only allowed `/tmp` path is `/tmp/final.patch`.
- Produce a valid unified git diff generated from `git diff --binary`.
- Before final output, run `git apply --check /tmp/final.patch`.
"""


def copy_selected_candidate(src: str, dst: Path) -> None:
    src_path = Path(src)
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_path, dst)


def write_selected_metadata(dst: Path, args: argparse.Namespace, best: dict[str, Any], reports: list[dict[str, Any]]) -> None:
    metadata_path = dst / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "system": args.selected_system,
            "feedback_candidate_system": args.candidate_system,
            "feedback_root": args.feedback_root,
            "feedback_attempts": len(reports),
            "feedback_memory_file": args.memory_file,
            "prompt_controller": args.prompt_controller,
            "bandit_state": (
                str(get_bandit_state_path(args))
                if is_bandit_controller(args.prompt_controller)
                else ""
            ),
            "hier_tau": args.hier_tau if args.prompt_controller == "hierarchical_bandit" else "",
            "selected_candidate": best["candidate_index"],
            "selected_prompt_arm": best.get("prompt_arm", "v3_control"),
            "selection_score": best["score"],
            "selection_reason": "highest score from patch compliance, patch apply, visible tests, and patch size",
            "notes": "mini-SWE-agent + feedback/evolution: memory guidance, visible-test feedback, failure summary, patch compliance check, candidate reranking",
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def clean_worktree(worktree: Path, base_commit: str) -> subprocess.CompletedProcess[str]:
    target = base_commit.strip() or "HEAD"
    reset = run(["git", "reset", "--hard", target], cwd=worktree, timeout=60)
    if reset.returncode != 0:
        return reset
    return run(["git", "clean", "-fd"], cwd=worktree, timeout=60)


def run(args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(args, 124, exc.stdout or "", exc.stderr or f"timed out after {timeout} seconds")


def run_shell(command: str, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=str(cwd), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(command, 124, exc.stdout or "", exc.stderr or f"timed out after {timeout} seconds")


def summarize_output(stdout: str | bytes | None, stderr: str | bytes | None, max_lines: int = 40) -> str:
    text = decode_output(stderr) + "\n" + decode_output(stdout)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "No output."
    return "\n".join(lines[-max_lines:])


def decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
