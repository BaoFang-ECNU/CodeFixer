"""Compare Baseline, +Feedback, and +Learning/Evolution systems."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.evaluate import run_evaluation


SYSTEMS = ["baseline", "feedback", "learning"]


def compare_systems(config_path: str = "configs/default.yaml") -> dict:
    """Run all system versions on the same task set."""

    root = Path.cwd()
    payloads = {system: run_evaluation(config_path, system_version=system) for system in SYSTEMS}
    out = {
        "systems": SYSTEMS,
        "metrics": {system: payloads[system]["metrics"] for system in SYSTEMS},
        "grouped_metrics": {system: payloads[system].get("grouped_metrics", {}) for system in SYSTEMS},
        "results": {system: payloads[system]["results"] for system in SYSTEMS},
    }
    (root / "evaluation" / "system_comparison_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    (root / "evaluation" / "system_comparison_summary.md").write_text(_summary(out), encoding="utf-8")
    return out


def _summary(out: dict) -> str:
    lines = [
        "# System Comparison Summary",
        "",
        "| system | pass@1 | pass@k | visible pass | hidden/regression pass | avg tools | avg tests | patch lines | unsafe rate | cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system in out["systems"]:
        metrics = out["metrics"][system]
        lines.append(
            f"| {system} | {metrics['pass_at_1']} | {metrics['pass_at_k']} | {metrics['visible_test_pass_rate']} | "
            f"{metrics['hidden_regression_test_pass_rate']} | {metrics['avg_tool_calls']} | {metrics['avg_test_runs']} | "
            f"{metrics['avg_patch_diff_lines']} | {metrics['unsafe_edit_rate']} | {metrics['cost_estimate']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    compare_systems(args.config)
    print("Wrote evaluation/system_comparison_results.json and evaluation/system_comparison_summary.md")


if __name__ == "__main__":
    main()

