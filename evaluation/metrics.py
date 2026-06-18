"""Metrics for code repair experiments."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_metrics(results: list[dict[str, Any]], pass_at_k: int = 3, cost_per_tool_call: float = 0.001) -> dict[str, float]:
    """Compute aggregate metrics from task results."""

    if not results:
        return _empty_metrics()

    n = len(results)
    successes = sum(1 for item in results if item.get("success"))
    task_groups = _group_attempts_by_task(results)
    task_count = len(task_groups) or n
    hidden_known = [item for item in results if item.get("hidden_success") is not None]
    tool_calls = sum(item.get("tool_calls", 0) for item in results)
    api_cost = tool_calls * cost_per_tool_call
    runtime_cost = sum(item.get("runtime_sec", 0.0) for item in results)
    java_results = [item for item in results if item.get("language") == "java"]
    defects4j_results = [item for item in results if item.get("project_source") == "defects4j"]
    return {
        "pass_at_1": round(_pass_at_k(task_groups, 1) if task_groups else successes / n, 4),
        "pass_at_k": round(_pass_at_k(task_groups, pass_at_k) if task_groups else min(1.0, successes / max(1, min(pass_at_k, n))), 4),
        "visible_test_pass_rate": round(successes / n, 4),
        "hidden_regression_test_pass_rate": round(sum(1 for item in hidden_known if item.get("hidden_success")) / len(hidden_known), 4) if hidden_known else 0.0,
        "avg_reward": round(sum(item.get("reward", 0.0) for item in results) / n, 4),
        "avg_steps": round(sum(item.get("steps", 0) for item in results) / n, 4),
        "avg_tool_calls": round(tool_calls / n, 4),
        "avg_test_runs": round(sum(item.get("test_runs", 0) for item in results) / n, 4),
        "avg_runtime_sec": round(sum(item.get("runtime_sec", 0.0) for item in results) / n, 4),
        "avg_patch_size": round(sum(item.get("patch_size", 0) for item in results) / n, 4),
        "avg_patch_diff_lines": round(sum(item.get("patch_diff_lines", item.get("patch_size", 0)) for item in results) / n, 4),
        "patch_file_count": round(sum(item.get("patch_file_count", 0) for item in results) / n, 4),
        "unsafe_edit_rate": round(sum(1 for item in results if item.get("unsafe_edits", 0) > 0) / n, 4),
        "timeout_rate": round(sum(1 for item in results if item.get("timed_out")) / n, 4),
        "api_cost_estimate": round(api_cost, 4),
        "runtime_cost_sec": round(runtime_cost, 4),
        "cost_estimate": round(api_cost + runtime_cost * 0.0, 4),
        "num_tasks": float(task_count),
        "num_attempts": float(n),
        "trials_per_task_observed": round(n / max(1, task_count), 4),
        "java_compile_failure_rate": round(_java_compile_failures(java_results) / len(java_results), 4) if java_results else 0.0,
        "defects4j_triggering_test_pass_rate": round(sum(1 for item in defects4j_results if item.get("success")) / len(defects4j_results), 4) if defects4j_results else 0.0,
    }


def _empty_metrics() -> dict[str, float]:
    return {
            "pass_at_1": 0.0,
            "pass_at_k": 0.0,
            "visible_test_pass_rate": 0.0,
            "avg_reward": 0.0,
            "avg_steps": 0.0,
            "avg_tool_calls": 0.0,
            "avg_test_runs": 0.0,
            "avg_runtime_sec": 0.0,
            "avg_patch_size": 0.0,
            "avg_patch_diff_lines": 0.0,
            "patch_file_count": 0.0,
            "unsafe_edit_rate": 0.0,
            "timeout_rate": 0.0,
            "hidden_regression_test_pass_rate": 0.0,
            "api_cost_estimate": 0.0,
            "runtime_cost_sec": 0.0,
            "cost_estimate": 0.0,
            "num_tasks": 0.0,
            "num_attempts": 0.0,
            "trials_per_task_observed": 0.0,
            "java_compile_failure_rate": 0.0,
            "defects4j_triggering_test_pass_rate": 0.0,
    }


def _group_attempts_by_task(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, item in enumerate(results):
        key = str(item.get("task_id", f"attempt_{index}"))
        groups[key].append(item)
    for attempts in groups.values():
        attempts.sort(key=lambda item: int(item.get("trial_id", item.get("attempt_id", 1)) or 1))
    return dict(groups)


def _pass_at_k(task_groups: dict[str, list[dict[str, Any]]], k: int) -> float:
    if not task_groups:
        return 0.0
    capped_k = max(1, k)
    passed = sum(1 for attempts in task_groups.values() if any(item.get("success") for item in attempts[:capped_k]))
    return passed / len(task_groups)


def _java_compile_failures(results: list[dict[str, Any]]) -> int:
    failure_markers = ("compilation failed", "compile failed", "javac", "maven compilation failure")
    count = 0
    for item in results:
        text = f"{item.get('failure_reason', '')}\n{item.get('final_test_output', '')}".lower()
        if any(marker in text for marker in failure_markers):
            count += 1
    return count


def training_artifact_metrics(output_dir: str | None, total_steps: int = 0) -> dict[str, float]:
    """Count self-evolution data artifacts emitted during evaluation."""

    if not output_dir:
        return _empty_training_artifact_metrics()
    from pathlib import Path
    import json

    root = Path(output_dir)
    metrics = {
        "sft_record_count": float(_count_jsonl(root / "sft_train.jsonl")),
        "dpo_pair_count": float(_count_jsonl(root / "dpo_train.jsonl")),
        "opd_record_count": float(_count_jsonl(root / "opd_train.jsonl")),
        "rwr_record_count": float(_count_jsonl(root / "rwr_train.jsonl")),
        "rlvr_rollout_count": float(_count_jsonl(root / "rlvr_rollouts.jsonl")),
        "guidance_record_count": float(_count_jsonl(root / "guidance_train.jsonl")),
        "guidance_coverage": 0.0,
        "memory_pattern_count": 0.0,
    }
    metrics["guidance_coverage"] = round(metrics["guidance_record_count"] / max(1, total_steps), 4)
    memory_file = root / "memory_patterns.json"
    if memory_file.exists():
        try:
            payload = json.loads(memory_file.read_text(encoding="utf-8"))
            metrics["memory_pattern_count"] = float(len(payload))
        except json.JSONDecodeError:
            metrics["memory_pattern_count"] = 0.0
    return metrics


def _empty_training_artifact_metrics() -> dict[str, float]:
    return {
        "sft_record_count": 0.0,
        "dpo_pair_count": 0.0,
        "opd_record_count": 0.0,
        "rwr_record_count": 0.0,
        "rlvr_rollout_count": 0.0,
        "guidance_record_count": 0.0,
        "guidance_coverage": 0.0,
        "memory_pattern_count": 0.0,
    }


def _count_jsonl(path: "Path") -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def summary_markdown(metrics: dict[str, float], results: list[dict[str, Any]], title: str = "Evaluation Summary") -> str:
    """Render metrics and per-task results as Markdown."""

    lines = [f"# {title}", "", "## Metrics"]
    lines.extend(f"- {key}: {value}" for key, value in metrics.items())
    lines.extend(["", "## Tasks", "| task_id | trial | version | bug_type | lang | visible | hidden | failure_reason | reward | tools | tests | patch_lines |", "|---|---:|---|---|---|---:|---:|---|---:|---:|---:|---:|"])
    for item in results:
        hidden = item.get("hidden_success")
        hidden_text = "" if hidden is None else str(hidden)
        lines.append(f"| {item['task_id']} | {item.get('trial_id', 1)} | {item.get('system_version', '')} | {item.get('bug_type', '')} | {item.get('language', '')} | {item.get('visible_success', item.get('success'))} | {hidden_text} | {item.get('failure_reason', '')} | {item['reward']:.4f} | {item['tool_calls']} | {item.get('test_runs', 0)} | {item.get('patch_diff_lines', item.get('patch_size', 0))} |")
    return "\n".join(lines) + "\n"


def grouped_metrics(results: list[dict[str, Any]], group_keys: list[str]) -> dict[str, dict[str, float]]:
    """Compute pass-rate style metrics grouped by metadata keys."""

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        key = " / ".join(str(item.get(group_key, "unknown")) for group_key in group_keys)
        groups.setdefault(key, []).append(item)
    return {key: compute_metrics(items) for key, items in groups.items()}
