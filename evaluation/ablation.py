"""Ablation runner for CodeFixer."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from evaluation.evaluate import run_evaluation
from env.task_loader import load_yaml


ABLATIONS = {
    "baseline_rule_agent": {},
    "no_memory": {"agent": {"use_memory": False}},
    "no_test_feedback": {"agent": {"use_test_feedback": False}},
    "no_self_evolution": {"agent": {"use_self_evolution": False}},
    "reward_no_patch_penalty": {"reward_weights": {"patch_size_penalty": 0.0}},
    "no_guidance": {"training": {"guidance": {"enabled": False}}, "evolution": {"export_guidance": False}},
    "no_reward_breakdown": {"evaluation": {"record_reward_breakdown": False}},
    "no_self_evolution_export": {"agent": {"use_self_evolution": False}},
    "no_dpo_opd_export": {"evolution": {"export_dpo_opd": False}},
    "no_rlvr_export": {"evolution": {"export_rlvr": False}},
    "no_hidden_reward": {"evaluation": {"run_hidden_tests": False}},
    "max_steps_3": {"agent": {"max_steps": 3}},
    "max_steps_8": {"agent": {"max_steps": 8}},
}


def run_ablation(config_path: str = "configs/default.yaml", max_tasks: int | None = None, output_dir: str | None = None) -> dict:
    """Run configured ablations and write a summary."""

    project_root = Path.cwd()
    base_config = load_yaml(config_path)
    ablation_config = load_yaml(project_root / "configs" / "ablations.yaml")
    configured_ablations = ablation_config.get("ablations", ABLATIONS)
    out_dir = Path(output_dir or ablation_config.get("output_dir") or base_config.get("evaluation", {}).get("ablation_output_dir") or base_config.get("evaluation", {}).get("output_dir", "outputs/evaluation")) / "ablations"
    all_results = {}
    rows = []
    for name, overrides in configured_ablations.items():
        system_version = "baseline" if name == "baseline_rule_agent" else "learning"
        payload = run_evaluation(
            config_path,
            overrides=copy.deepcopy(overrides),
            system_version=system_version,
            max_tasks=max_tasks,
            output_dir=str(out_dir / name),
        )
        all_results[name] = payload
        row = {
            "task_id": name,
            "success": payload["metrics"]["pass_at_1"] > 0,
            "first_pass_step": None,
            "failure_reason": "aggregate",
            "reward": payload["metrics"]["avg_reward"],
            "steps": payload["metrics"]["avg_steps"],
            "tool_calls": payload["metrics"]["avg_tool_calls"],
            "test_runs": payload["metrics"]["avg_test_runs"],
            "patch_size": payload["metrics"]["avg_patch_size"],
            "patch_diff_lines": payload["metrics"].get("avg_patch_diff_lines", payload["metrics"]["avg_patch_size"]),
            "hidden_success": payload["metrics"].get("hidden_regression_test_pass_rate"),
        }
        rows.append(row)

    target_dir = project_root / out_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / "ablation_results.json"
    out_file.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = _ablation_summary(all_results, rows, max_tasks=max_tasks)
    (target_dir / "ablation_summary.md").write_text(summary, encoding="utf-8")
    return all_results


def _ablation_summary(all_results: dict, rows: list[dict], max_tasks: int | None = None) -> str:
    """Render a compact ablation table without synthetic zero metrics."""

    title = "# Ablation Summary"
    scope = f"\n\nTask scope: first {max_tasks} tasks.\n" if max_tasks else "\n\nTask scope: all configured tasks.\n"
    lines = [
        title,
        scope,
        "| ablation | pass@1 | pass@k | visible pass | hidden/regression pass | avg reward | avg tools | avg tests | patch lines | unsafe rate | SFT | DPO | OPD | RLVR | guidance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, payload in all_results.items():
        metrics = payload["metrics"]
        lines.append(
            f"| {name} | {metrics['pass_at_1']} | {metrics['pass_at_k']} | {metrics['visible_test_pass_rate']} | "
            f"{metrics['hidden_regression_test_pass_rate']} | {metrics['avg_reward']} | {metrics['avg_tool_calls']} | "
            f"{metrics['avg_test_runs']} | {metrics['avg_patch_diff_lines']} | {metrics['unsafe_edit_rate']} | "
            f"{metrics.get('sft_record_count', 0)} | {metrics.get('dpo_pair_count', 0)} | {metrics.get('opd_record_count', 0)} | "
            f"{metrics.get('rlvr_rollout_count', 0)} | {metrics.get('guidance_coverage', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Rows",
            "",
            "| ablation | success | reward | tools | tests | patch_lines | hidden/regression |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['task_id']} | {row['success']} | {row['reward']:.4f} | {row['tool_calls']} | "
            f"{row['test_runs']} | {row['patch_diff_lines']} | {row['hidden_success']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    run_ablation(args.config, max_tasks=args.max_tasks, output_dir=args.output_dir)
    print("Wrote ablation results under the configured output directory")


if __name__ == "__main__":
    main()
