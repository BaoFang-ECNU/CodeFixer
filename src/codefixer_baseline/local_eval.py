from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

NA = "NA"


@dataclass(frozen=True)
class TaskSpec:
    id: str
    repo_path: Path
    base_commit: str = ""
    issue: str = ""
    relevant_files: tuple[str, ...] = ()
    visible_test_command: str | None = None
    hidden_test_command: str | None = None
    fix_test_command: str | None = None
    regression_test_command: str | None = None
    hidden_test_patch: Path | None = None
    timeout_sec: int = 120


@dataclass(frozen=True)
class SystemSpec:
    name: str
    attempts_dir: Path
    description: str = ""


METRIC_FIELDS = [
    "system",
    "num_tasks",
    "num_candidates",
    "pass_at_1",
    "pass_at_k",
    "visible_test_pass_rate",
    "fix_test_pass_rate",
    "regression_test_pass_rate",
    "hidden_regression_test_pass_rate",
    "average_tool_calls",
    "average_test_runs",
    "average_patch_lines",
    "average_patch_files",
    "unsafe_edit_rate",
    "submission_compliance_rate",
    "empty_patch_rate",
    "artifact_exposure_rate",
    "average_cost",
    "average_wall_time_sec",
    "total_wall_time_sec",
]

CANDIDATE_FIELDS = [
    "system",
    "task_id",
    "candidate_index",
    "candidate_dir",
    "patch_applied",
    "visible_pass",
    "fix_pass",
    "regression_pass",
    "hidden_pass",
    "success",
    "submission_compliant",
    "empty_patch",
    "tool_calls",
    "test_runs",
    "patch_lines",
    "patch_files",
    "unsafe_edit",
    "test_file_edit",
    "test_deletion",
    "hardcoded_answer_risk",
    "artifact_file_edits",
    "workdir_drift",
    "benchmark_artifact_exposure",
    "benchmark_artifact_content_access",
    "irrelevant_file_edits",
    "cost",
    "wall_time_sec",
    "notes",
]


def load_manifest(path: str | Path) -> tuple[list[SystemSpec], list[TaskSpec]]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    base = manifest_path.parent.parent
    systems = [
        SystemSpec(
            name=str(item["name"]),
            attempts_dir=_resolve_path(base, item["attempts_dir"]),
            description=str(item.get("description", "")),
        )
        for item in data.get("systems", [])
    ]
    tasks = [
        TaskSpec(
            id=str(item["id"]),
            base_commit=str(item.get("base_commit", "")),
            repo_path=_resolve_path(base, item["repo_path"]),
            issue=str(item.get("issue", "")),
            relevant_files=tuple(str(x) for x in item.get("relevant_files", [])),
            visible_test_command=item.get("visible_test_command"),
            hidden_test_command=item.get("hidden_test_command"),
            fix_test_command=item.get("fix_test_command"),
            regression_test_command=item.get("regression_test_command"),
            hidden_test_patch=_resolve_path(base, item["hidden_test_patch"]) if item.get("hidden_test_patch") else None,
            timeout_sec=int(item.get("timeout_sec", 120)),
        )
        for item in data.get("tasks", [])
    ]
    return systems, tasks


def _resolve_path(base: Path, value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def find_candidates(attempts_dir: Path, task_id: str) -> list[Path]:
    task_dir = attempts_dir / task_id
    if not task_dir.exists():
        return []
    if (task_dir / "patch.diff").exists():
        return [task_dir]
    candidates = [p for p in task_dir.iterdir() if p.is_dir() and (p / "patch.diff").exists()]
    return sorted(candidates)


def evaluate_manifest(manifest_path: str | Path, output_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    systems, tasks = load_manifest(manifest_path)
    candidate_rows: list[dict[str, Any]] = []
    for system in systems:
        for task in tasks:
            candidates = find_candidates(system.attempts_dir, task.id)
            for index, candidate_dir in enumerate(candidates):
                print(f"[local-eval] evaluating {system.name}/{task.id}/candidate_{index}", flush=True)
                candidate_rows.append(evaluate_candidate(system, task, candidate_dir, index))

    summary_rows = [summarize_system(system.name, tasks, candidate_rows) for system in systems]
    write_outputs(candidate_rows, summary_rows, Path(output_dir))
    return candidate_rows, summary_rows


def evaluate_candidate(system: SystemSpec, task: TaskSpec, candidate_dir: Path, candidate_index: int) -> dict[str, Any]:
    start = time.monotonic()
    patch_path = candidate_dir / "patch.diff"
    metadata = _read_json(candidate_dir / "metadata.json")
    trajectory = _read_json(candidate_dir / "trajectory.json")
    patch_text = patch_path.read_text(encoding="utf-8", errors="ignore") if patch_path.exists() else ""
    patch_stats = analyze_patch(patch_text, task.relevant_files)
    tool_stats = analyze_trajectory(trajectory)
    log_audit = analyze_agent_artifacts(candidate_dir)

    patch_applied = False
    visible_pass: bool | str = NA
    fix_pass: bool | str = NA
    regression_pass: bool | str = NA
    hidden_pass: bool | str = NA
    notes: list[str] = []
    eval_log_dir = candidate_dir / "eval_logs"
    eval_log_dir.mkdir(exist_ok=True)
    if patch_stats["empty_patch"]:
        notes.append("empty_patch")
    if log_audit["workdir_drift"]:
        notes.append("workdir_drift")
    if log_audit["benchmark_artifact_exposure"]:
        notes.append("benchmark_artifact_exposure")
    if log_audit["benchmark_artifact_content_access"]:
        notes.append("benchmark_artifact_content_access")

    with tempfile.TemporaryDirectory(prefix=f"codefixer-eval-{task.id}-") as tmp:
        worktree = Path(tmp) / "repo"
        try:
            print(f"[local-eval] copying repo for {task.id}", flush=True)
            shutil.copytree(task.repo_path, worktree)
        except OSError as exc:
            notes.append(f"copy_failed:{exc}")
        else:
            clean_result = clean_worktree(worktree, task.base_commit)
            write_command_log(eval_log_dir, "source_clean", clean_result)
            if clean_result.returncode != 0:
                notes.append("source_clean_failed")
                notes.append(_trim(clean_result.stderr or clean_result.stdout))
            print(f"[local-eval] applying patch for {task.id}", flush=True)
            apply_result = apply_patch(worktree, patch_path)
            write_command_log(eval_log_dir, "candidate_patch", apply_result)
            patch_applied = apply_result.returncode == 0
            if not patch_applied:
                notes.append("patch_apply_failed")
                notes.append(_trim(apply_result.stderr or apply_result.stdout))
            else:
                if task.visible_test_command:
                    print(f"[local-eval] running visible tests for {task.id}", flush=True)
                    visible = run_shell(task.visible_test_command, worktree, task.timeout_sec)
                    write_command_log(eval_log_dir, "visible", visible)
                    visible_pass = visible.returncode == 0
                    if not visible_pass:
                        notes.append("visible_failed")
                runs_hidden_tests = bool(task.fix_test_command or task.regression_test_command or task.hidden_test_command)
                if runs_hidden_tests and task.hidden_test_patch:
                    print(f"[local-eval] applying hidden test patch for {task.id}", flush=True)
                    hidden_patch_result = apply_patch(worktree, task.hidden_test_patch)
                    write_command_log(eval_log_dir, "hidden_test_patch", hidden_patch_result)
                    if hidden_patch_result.returncode != 0:
                        notes.append("hidden_test_patch_apply_failed")
                        notes.append(_trim(hidden_patch_result.stderr or hidden_patch_result.stdout))
                if task.fix_test_command:
                    print(f"[local-eval] running fix tests for {task.id}", flush=True)
                    fix = run_shell(task.fix_test_command, worktree, task.timeout_sec)
                    write_command_log(eval_log_dir, "fix", fix)
                    fix_pass = fix.returncode == 0
                    if not fix_pass:
                        notes.append("fix_failed")
                        if fix.returncode == 124:
                            notes.append("fix_timeout")
                if task.regression_test_command:
                    print(f"[local-eval] running regression tests for {task.id}", flush=True)
                    regression = run_shell(task.regression_test_command, worktree, task.timeout_sec)
                    write_command_log(eval_log_dir, "regression", regression)
                    regression_pass = regression.returncode == 0
                    if not regression_pass:
                        notes.append("regression_failed")
                        if regression.returncode == 124:
                            notes.append("regression_timeout")
                if task.fix_test_command or task.regression_test_command:
                    hidden_pass = _combine_passes(fix_pass, regression_pass)
                elif task.hidden_test_command:
                    print(f"[local-eval] running hidden tests for {task.id}", flush=True)
                    hidden = run_shell(task.hidden_test_command, worktree, task.timeout_sec)
                    write_command_log(eval_log_dir, "hidden", hidden)
                    hidden_pass = hidden.returncode == 0
                    if not hidden_pass:
                        notes.append("hidden_failed")
                        if hidden.returncode == 124:
                            notes.append("hidden_timeout")

    submission_compliant = (
        patch_applied
        and not patch_stats["empty_patch"]
        and not patch_stats["test_file_edit"]
        and not patch_stats["artifact_file_edits"]
        and not log_audit["workdir_drift"]
        and not log_audit["benchmark_artifact_content_access"]
    )
    success = _is_success(visible_pass, hidden_pass)
    wall_time = round(time.monotonic() - start, 4)
    cost = metadata.get("cost", metadata.get("total_cost", NA))

    return normalize_candidate_row(
        {
            "system": system.name,
            "task_id": task.id,
            "candidate_index": candidate_index,
            "candidate_dir": str(candidate_dir),
            "patch_applied": patch_applied,
            "visible_pass": visible_pass,
            "fix_pass": fix_pass,
            "regression_pass": regression_pass,
            "hidden_pass": hidden_pass,
            "success": success,
            "submission_compliant": submission_compliant,
            "empty_patch": patch_stats["empty_patch"],
            "tool_calls": metadata.get("tool_calls", tool_stats["tool_calls"]),
            "test_runs": metadata.get("test_runs", tool_stats["test_runs"]),
            "patch_lines": patch_stats["patch_lines"],
            "patch_files": patch_stats["patch_files"],
            "unsafe_edit": patch_stats["unsafe_edit"],
            "test_file_edit": patch_stats["test_file_edit"],
            "test_deletion": patch_stats["test_deletion"],
            "hardcoded_answer_risk": patch_stats["hardcoded_answer_risk"],
            "artifact_file_edits": patch_stats["artifact_file_edits"],
            "workdir_drift": log_audit["workdir_drift"],
            "benchmark_artifact_exposure": log_audit["benchmark_artifact_exposure"],
            "benchmark_artifact_content_access": log_audit["benchmark_artifact_content_access"],
            "irrelevant_file_edits": patch_stats["irrelevant_file_edits"],
            "cost": cost,
            "wall_time_sec": metadata.get("wall_time_sec", wall_time),
            "notes": ";".join(notes) if notes else "",
        }
    )


def apply_patch(worktree: Path, patch_path: Path) -> subprocess.CompletedProcess[str]:
    if not patch_path.exists():
        return _annotate_result(
            subprocess.CompletedProcess(["git", "apply"], 2, "", "missing patch.diff"),
            cwd=worktree,
            timeout_sec=60,
            duration_sec=0.0,
            shell=False,
        )
    args = ["git", "apply", "--whitespace=nowarn", str(patch_path)]
    return _run_subprocess(
        args,
        cwd=worktree,
        timeout_sec=60,
        shell=False,
    )


def clean_worktree(worktree: Path, base_commit: str = "") -> subprocess.CompletedProcess[str]:
    if not (worktree / ".git").exists():
        return _annotate_result(
            subprocess.CompletedProcess(["git", "reset"], 0, "", ""),
            cwd=worktree,
            timeout_sec=60,
            duration_sec=0.0,
            shell=False,
        )
    target = base_commit.strip() or "HEAD"
    start = time.monotonic()
    reset = subprocess.run(
        ["git", "reset", "--hard", target],
        cwd=str(worktree),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if reset.returncode != 0:
        return _annotate_result(
            reset,
            cwd=worktree,
            timeout_sec=60,
            duration_sec=time.monotonic() - start,
            shell=False,
        )
    clean = subprocess.run(
        ["git", "clean", "-fd"],
        cwd=str(worktree),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return _annotate_result(
        subprocess.CompletedProcess(
        ["git", "reset", "--hard", target, "&&", "git", "clean", "-fd"],
        clean.returncode,
        (reset.stdout or "") + (clean.stdout or ""),
        (reset.stderr or "") + (clean.stderr or ""),
        ),
        cwd=worktree,
        timeout_sec=60,
        duration_sec=time.monotonic() - start,
        shell=False,
    )


def run_shell(command: str, cwd: Path, timeout_sec: int) -> subprocess.CompletedProcess[str]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
        )
        return _annotate_result(
            result,
            cwd=cwd,
            timeout_sec=timeout_sec,
            duration_sec=time.monotonic() - start,
            shell=True,
        )
    except subprocess.TimeoutExpired as exc:
        return _annotate_result(
            subprocess.CompletedProcess(
                command,
                124,
                exc.stdout or "",
                exc.stderr or f"timed out after {timeout_sec} seconds",
            ),
            cwd=cwd,
            timeout_sec=timeout_sec,
            duration_sec=time.monotonic() - start,
            shell=True,
        )


def write_command_log(log_dir: Path, name: str, result: subprocess.CompletedProcess[str]) -> None:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    (log_dir / f"{safe_name}.stdout.txt").write_text(_as_text(result.stdout), encoding="utf-8", errors="ignore")
    (log_dir / f"{safe_name}.stderr.txt").write_text(_as_text(result.stderr), encoding="utf-8", errors="ignore")
    (log_dir / f"{safe_name}.meta.json").write_text(
        json.dumps(
            {
                "args": result.args,
                "command": _command_to_string(result.args),
                "returncode": result.returncode,
                "cwd": getattr(result, "cwd", NA),
                "timeout_sec": getattr(result, "timeout_sec", NA),
                "duration_sec": getattr(result, "duration_sec", NA),
                "shell": getattr(result, "shell", NA),
                "stdout_path": f"{safe_name}.stdout.txt",
                "stderr_path": f"{safe_name}.stderr.txt",
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def _run_subprocess(
    args: list[str] | str,
    cwd: Path,
    timeout_sec: int,
    shell: bool,
) -> subprocess.CompletedProcess[str]:
    start = time.monotonic()
    result = subprocess.run(
        args,
        cwd=str(cwd),
        shell=shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_sec,
    )
    return _annotate_result(
        result,
        cwd=cwd,
        timeout_sec=timeout_sec,
        duration_sec=time.monotonic() - start,
        shell=shell,
    )


def _annotate_result(
    result: subprocess.CompletedProcess[str],
    cwd: Path,
    timeout_sec: int,
    duration_sec: float,
    shell: bool,
) -> subprocess.CompletedProcess[str]:
    result.cwd = str(cwd)
    result.timeout_sec = timeout_sec
    result.duration_sec = round(duration_sec, 4)
    result.shell = shell
    return result


def _command_to_string(args: Any) -> str:
    if isinstance(args, str):
        return args
    if isinstance(args, (list, tuple)):
        return " ".join(str(item) for item in args)
    return str(args)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def analyze_patch(patch_text: str, relevant_files: tuple[str, ...] = ()) -> dict[str, Any]:
    files = _changed_files(patch_text)
    patch_lines = sum(1 for line in patch_text.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    test_file_edit = any(_is_test_file(path) for path in files)
    test_deletion = test_file_edit and any(
        line.startswith("-") and not line.startswith("---") for line in patch_text.splitlines()
    )
    hardcoded_answer_risk = bool(re.search(r"(return|=)\s*['\"]?(PASS|SUCCESS|42|expected|gold)['\"]?", patch_text, re.IGNORECASE))
    artifact_files = [path for path in files if _is_artifact_file(path)]
    irrelevant = 0
    if relevant_files:
        normalized = {Path(p).as_posix() for p in relevant_files}
        for path in files:
            posix = Path(path).as_posix()
            if posix not in normalized and not any(posix.endswith("/" + rel) or rel.endswith("/" + posix) for rel in normalized):
                irrelevant += 1
    unsafe_edit = test_file_edit or hardcoded_answer_risk or bool(artifact_files)
    return {
        "empty_patch": not bool(patch_text.strip()) or not bool(files),
        "patch_lines": patch_lines,
        "patch_files": len(files),
        "test_file_edit": test_file_edit,
        "test_deletion": test_deletion,
        "hardcoded_answer_risk": hardcoded_answer_risk,
        "artifact_file_edits": len(artifact_files),
        "irrelevant_file_edits": irrelevant,
        "unsafe_edit": unsafe_edit,
    }


def _changed_files(patch_text: str) -> list[str]:
    files: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            files.append(line.removeprefix("+++ b/"))
        elif line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                files.append(parts[3].removeprefix("b/"))
    return sorted(set(files))


def _is_test_file(path: str) -> bool:
    posix = Path(path).as_posix().lower()
    parts = posix.split("/")
    name = parts[-1] if parts else posix
    return (
        "tests" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name in {"conftest.py", "pytest.ini", "tox.ini"}
    )


def _is_artifact_file(path: str) -> bool:
    posix = Path(path).as_posix().lower()
    name = posix.split("/")[-1]
    return (
        name.startswith(("temp_", "debug_", "reproduce_"))
        or name in {"simple_test.py", "quick_test.py", "verification.py", "fix.patch"}
        or name.endswith((".backup", ".bak", ".orig", ".original", ".fixed", ".patch"))
    )


def analyze_agent_artifacts(candidate_dir: Path) -> dict[str, bool]:
    texts: list[str] = []
    for name in ("mini_stdout.log", "trajectory.json"):
        path = candidate_dir / name
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
    text = "\n".join(texts)
    artifact_names = ("reference.patch", "record.json", "hidden_test.patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS")
    content_patterns = (
        r"\bcat\s+.*(?:reference\.patch|record\.json|hidden_test\.patch)",
        r"\bsed\s+.*(?:reference\.patch|record\.json|hidden_test\.patch)",
        r"\bhead\s+.*(?:reference\.patch|record\.json|hidden_test\.patch)",
        r"\btail\s+.*(?:reference\.patch|record\.json|hidden_test\.patch)",
        r"open\(.*(?:reference\.patch|record\.json|hidden_test\.patch)",
    )
    return {
        "workdir_drift": bool(re.search(r"(/tmp/django|\bcd\s+/tmp|\bcp\s+-r\s+.*?/tmp)", text)),
        "benchmark_artifact_exposure": any(name in text for name in artifact_names),
        "benchmark_artifact_content_access": any(re.search(pattern, text) for pattern in content_patterns),
    }


def analyze_trajectory(value: Any) -> dict[str, int]:
    if not value:
        return {"tool_calls": 0, "test_runs": 0}
    text = json.dumps(value, ensure_ascii=False).lower()
    tool_calls = len(re.findall(r'"tool(_name)?":|"tool_calls":|"action":', text))
    test_runs = len(re.findall(r"pytest|unittest|mvn test|npm test|pnpm test|yarn test|run_tests?", text))
    return {"tool_calls": tool_calls, "test_runs": test_runs}


def summarize_system(system_name: str, tasks: list[TaskSpec], candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in candidate_rows if row["system"] == system_name]
    first_by_task = _first_by_task(rows)
    any_success_tasks = {row["task_id"] for row in rows if row["success"] is True}
    num_tasks = len(tasks)
    return {
        "system": system_name,
        "num_tasks": num_tasks,
        "num_candidates": len(rows),
        "pass_at_1": _rate(sum(1 for row in first_by_task.values() if row["success"] is True), num_tasks),
        "pass_at_k": _rate(len(any_success_tasks), num_tasks),
        "visible_test_pass_rate": _bool_rate(row["visible_pass"] for row in rows),
        "fix_test_pass_rate": _bool_rate(row.get("fix_pass", NA) for row in rows),
        "regression_test_pass_rate": _bool_rate(row.get("regression_pass", NA) for row in rows),
        "hidden_regression_test_pass_rate": _bool_rate(row.get("hidden_pass", NA) for row in rows),
        "average_tool_calls": _mean(row.get("tool_calls", NA) for row in rows),
        "average_test_runs": _mean(row.get("test_runs", NA) for row in rows),
        "average_patch_lines": _mean(row.get("patch_lines", NA) for row in rows),
        "average_patch_files": _mean(row.get("patch_files", NA) for row in rows),
        "unsafe_edit_rate": _bool_rate(row.get("unsafe_edit", NA) for row in rows),
        "submission_compliance_rate": _bool_rate(row.get("submission_compliant", NA) for row in rows),
        "empty_patch_rate": _bool_rate(row.get("empty_patch", NA) for row in rows),
        "artifact_exposure_rate": _bool_rate(row.get("benchmark_artifact_exposure", NA) for row in rows),
        "average_cost": _mean(row.get("cost", NA) for row in rows),
        "average_wall_time_sec": _mean(row.get("wall_time_sec", NA) for row in rows),
        "total_wall_time_sec": _sum(row.get("wall_time_sec", NA) for row in rows),
    }


def _first_by_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: (item["task_id"], int(item["candidate_index"]))):
        result.setdefault(str(row["task_id"]), row)
    return result


def _is_success(visible_pass: bool | str, hidden_pass: bool | str) -> bool:
    if hidden_pass is not NA and hidden_pass != NA:
        return bool(hidden_pass)
    if visible_pass is not NA and visible_pass != NA:
        return bool(visible_pass)
    return False


def _combine_passes(*values: bool | str) -> bool | str:
    bools = [value for value in values if isinstance(value, bool)]
    if not bools:
        return NA
    return all(bools)


def _bool_rate(values: Any) -> float | str:
    vals = [v for v in values if isinstance(v, bool)]
    if not vals:
        return NA
    return round(sum(1 for v in vals if v) / len(vals), 4)


def _rate(num: int, den: int) -> float | str:
    if den <= 0:
        return NA
    return round(num / den, 4)


def _mean(values: Any) -> float | str:
    nums: list[float] = []
    for value in values:
        try:
            if value == NA or value is None or value == "":
                continue
            number = float(value)
            if not math.isnan(number):
                nums.append(number)
        except (TypeError, ValueError):
            continue
    if not nums:
        return NA
    return round(sum(nums) / len(nums), 4)


def _sum(values: Any) -> float | str:
    nums: list[float] = []
    for value in values:
        try:
            if value == NA or value is None or value == "":
                continue
            number = float(value)
            if not math.isnan(number):
                nums.append(number)
        except (TypeError, ValueError):
            continue
    if not nums:
        return NA
    return round(sum(nums), 4)


def normalize_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field, NA) if row.get(field, NA) not in (None, "") else NA for field in CANDIDATE_FIELDS}


def write_outputs(candidate_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "candidate_metrics.csv", CANDIDATE_FIELDS, candidate_rows)
    _write_csv(output_dir / "system_metrics.csv", METRIC_FIELDS, summary_rows)
    (output_dir / "system_metrics.md").write_text(_markdown_table(METRIC_FIELDS, summary_rows), encoding="utf-8")


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(fields: list[str], rows: list[dict[str, Any]]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, NA)) for field in fields) + " |")
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _trim(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text[:limit]
