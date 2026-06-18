"""Compare Baseline, +Feedback, and +Learning/Evolution systems."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.evaluate import run_evaluation
from env.task_loader import load_yaml


SYSTEMS = ["baseline", "feedback", "learning"]


def compare_systems(config_path: str = "configs/default.yaml", max_tasks: int | None = None, output_dir: str | None = None) -> dict:
    """Run all system versions on the same task set."""

    root = Path.cwd()
    config = load_yaml(config_path)
    eval_config = config.get("evaluation", {})
    systems = list(eval_config.get("systems", SYSTEMS))
    out_dir = Path(output_dir or eval_config.get("comparison_output_dir") or eval_config.get("output_dir", "outputs/evaluation"))
    payloads = {
        system: run_evaluation(
            config_path,
            system_version=system,
            max_tasks=max_tasks,
            output_dir=str(out_dir / "systems" / system),
        )
        for system in systems
    }
    out = {
        "systems": systems,
        "metrics": {system: payloads[system]["metrics"] for system in systems},
        "grouped_metrics": {system: payloads[system].get("grouped_metrics", {}) for system in systems},
        "results": {system: payloads[system]["results"] for system in systems},
    }
    target_dir = root / out_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "system_comparison_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    (target_dir / "system_comparison_summary.md").write_text(_summary(out), encoding="utf-8")
    return out


def _summary(out: dict) -> str:
    lines = [
        "# System Comparison Summary",
        "",
        "| system | pass@1 | pass@k | visible pass | hidden/regression pass | avg tools | avg tests | patch lines | unsafe rate | java compile fail | defects4j pass | SFT | DPO | OPD | RLVR | guidance | cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system in out["systems"]:
        metrics = out["metrics"][system]
        lines.append(
            f"| {system} | {metrics['pass_at_1']} | {metrics['pass_at_k']} | {metrics['visible_test_pass_rate']} | "
            f"{metrics['hidden_regression_test_pass_rate']} | {metrics['avg_tool_calls']} | {metrics['avg_test_runs']} | "
            f"{metrics['avg_patch_diff_lines']} | {metrics['unsafe_edit_rate']} | {metrics.get('java_compile_failure_rate', 0)} | "
            f"{metrics.get('defects4j_triggering_test_pass_rate', 0)} | {metrics.get('sft_record_count', 0)} | "
            f"{metrics.get('dpo_pair_count', 0)} | {metrics.get('opd_record_count', 0)} | {metrics.get('rlvr_rollout_count', 0)} | "
            f"{metrics.get('guidance_coverage', 0)} | {metrics['cost_estimate']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    compare_systems(args.config, max_tasks=args.max_tasks, output_dir=args.output_dir)
    print("Wrote system comparison results under the configured output directory")


if __name__ == "__main__":
    main()
