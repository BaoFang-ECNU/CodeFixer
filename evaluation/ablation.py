"""Ablation runner for CodeFixer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.evaluate import run_evaluation
from evaluation.metrics import summary_markdown


ABLATIONS = {
    "baseline_rule_agent": {},
    "no_memory": {"agent": {"use_memory": False}},
    "no_test_feedback": {"agent": {"use_test_feedback": False}},
    "no_self_evolution": {"agent": {"use_self_evolution": False}},
    "reward_no_patch_penalty": {"reward_weights": {"patch_size_penalty": 0.0}},
    "max_steps_3": {"agent": {"max_steps": 3}},
    "max_steps_8": {"agent": {"max_steps": 8}},
}


def run_ablation(config_path: str = "configs/default.yaml") -> dict:
    """Run configured ablations and write a summary."""

    project_root = Path.cwd()
    all_results = {}
    rows = []
    for name, overrides in ABLATIONS.items():
        payload = run_evaluation(config_path, overrides=overrides)
        all_results[name] = payload
        row = {
            "task_id": name,
            "success": payload["metrics"]["pass_at_1"] > 0,
            "first_pass_step": None,
            "failure_reason": "aggregate",
            "reward": payload["metrics"]["avg_reward"],
            "steps": payload["metrics"]["avg_steps"],
            "tool_calls": payload["metrics"]["avg_tool_calls"],
            "patch_size": payload["metrics"]["avg_patch_size"],
            "patch_diff_lines": payload["metrics"].get("avg_patch_diff_lines", payload["metrics"]["avg_patch_size"]),
        }
        rows.append(row)

    out_file = project_root / "evaluation" / "ablation_results.json"
    out_file.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics = {name: payload["metrics"]["pass_at_1"] for name, payload in all_results.items()}
    summary = "# Ablation Summary\n\n" + "\n".join(f"- {name}: pass_at_1={score}" for name, score in metrics.items()) + "\n\n"
    summary += summary_markdown({"pass_at_1": 0, "pass_at_k": 0, "visible_test_pass_rate": 0, "avg_reward": 0, "avg_steps": 0, "avg_tool_calls": 0, "avg_runtime_sec": 0, "avg_patch_size": 0, "avg_patch_diff_lines": 0, "unsafe_edit_rate": 0, "timeout_rate": 0, "cost_estimate": 0}, rows, title="Ablation Rows")
    (project_root / "evaluation" / "ablation_summary.md").write_text(summary, encoding="utf-8")
    return all_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    run_ablation(args.config)
    print("Wrote evaluation/ablation_results.json and evaluation/ablation_summary.md")


if __name__ == "__main__":
    main()
