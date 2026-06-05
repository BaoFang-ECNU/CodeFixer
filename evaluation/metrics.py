"""Metrics for code repair experiments."""

from __future__ import annotations

from typing import Any


def compute_metrics(results: list[dict[str, Any]], pass_at_k: int = 3, cost_per_tool_call: float = 0.001) -> dict[str, float]:
    """Compute aggregate metrics from task results."""

    if not results:
        return {
            "pass_at_1": 0.0,
            "pass_at_k": 0.0,
            "visible_test_pass_rate": 0.0,
            "avg_reward": 0.0,
            "avg_steps": 0.0,
            "avg_tool_calls": 0.0,
            "avg_runtime_sec": 0.0,
            "avg_patch_size": 0.0,
            "avg_patch_diff_lines": 0.0,
            "unsafe_edit_rate": 0.0,
            "timeout_rate": 0.0,
            "cost_estimate": 0.0,
        }

    n = len(results)
    successes = sum(1 for item in results if item.get("success"))
    tool_calls = sum(item.get("tool_calls", 0) for item in results)
    return {
        "pass_at_1": round(successes / n, 4),
        "pass_at_k": round(min(1.0, successes / max(1, min(pass_at_k, n))), 4),
        "visible_test_pass_rate": round(successes / n, 4),
        "avg_reward": round(sum(item.get("reward", 0.0) for item in results) / n, 4),
        "avg_steps": round(sum(item.get("steps", 0) for item in results) / n, 4),
        "avg_tool_calls": round(tool_calls / n, 4),
        "avg_runtime_sec": round(sum(item.get("runtime_sec", 0.0) for item in results) / n, 4),
        "avg_patch_size": round(sum(item.get("patch_size", 0) for item in results) / n, 4),
        "avg_patch_diff_lines": round(sum(item.get("patch_diff_lines", item.get("patch_size", 0)) for item in results) / n, 4),
        "unsafe_edit_rate": round(sum(1 for item in results if item.get("unsafe_edits", 0) > 0) / n, 4),
        "timeout_rate": round(sum(1 for item in results if item.get("timed_out")) / n, 4),
        "cost_estimate": round(tool_calls * cost_per_tool_call, 4),
    }


def summary_markdown(metrics: dict[str, float], results: list[dict[str, Any]], title: str = "Evaluation Summary") -> str:
    """Render metrics and per-task results as Markdown."""

    lines = [f"# {title}", "", "## Metrics"]
    lines.extend(f"- {key}: {value}" for key, value in metrics.items())
    lines.extend(["", "## Tasks", "| task_id | success | first_pass_step | failure_reason | reward | steps | tool_calls | patch_lines |", "|---|---:|---:|---|---:|---:|---:|---:|"])
    for item in results:
        first_pass = item.get("first_pass_step")
        first_pass_text = "" if first_pass is None else str(first_pass)
        lines.append(f"| {item['task_id']} | {item['success']} | {first_pass_text} | {item.get('failure_reason', '')} | {item['reward']:.4f} | {item['steps']} | {item['tool_calls']} | {item.get('patch_diff_lines', item.get('patch_size', 0))} |")
    return "\n".join(lines) + "\n"
