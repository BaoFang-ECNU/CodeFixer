#!/usr/bin/env python
"""Collect final experiment outputs into report-ready Markdown tables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize final CodeFixer experiments.")
    parser.add_argument("--root", default="outputs/final_experiments")
    args = parser.parse_args()

    root = Path(args.root)
    comparison = read_json(root / "system_comparison_results.json")
    ablation = read_json(root / "ablations" / "ablation_results.json")
    lines = ["# Final Experiment Tables", ""]

    lines.extend(["## System Comparison", ""])
    if comparison:
        lines.append("| system | pass@1 | pass@k | hidden/regression | tools | tests | java compile fail | defects4j pass |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for system, metrics in comparison.get("metrics", {}).items():
            lines.append(
                f"| {system} | {metrics.get('pass_at_1', 0)} | {metrics.get('pass_at_k', 0)} | "
                f"{metrics.get('hidden_regression_test_pass_rate', 0)} | {metrics.get('avg_tool_calls', 0)} | "
                f"{metrics.get('avg_test_runs', 0)} | {metrics.get('java_compile_failure_rate', 0)} | "
                f"{metrics.get('defects4j_triggering_test_pass_rate', 0)} |"
            )
    else:
        lines.append("No system comparison results found.")

    lines.extend(["", "## Ablation Overview", ""])
    if ablation:
        lines.append("| ablation | pass@1 | pass@k | SFT | DPO | OPD | RLVR | guidance |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for name, payload in ablation.items():
            metrics = payload.get("metrics", {})
            lines.append(
                f"| {name} | {metrics.get('pass_at_1', 0)} | {metrics.get('pass_at_k', 0)} | "
                f"{metrics.get('sft_record_count', 0)} | {metrics.get('dpo_pair_count', 0)} | "
                f"{metrics.get('opd_record_count', 0)} | {metrics.get('rlvr_rollout_count', 0)} | "
                f"{metrics.get('guidance_coverage', 0)} |"
            )
    else:
        lines.append("No ablation results found.")

    root.mkdir(parents=True, exist_ok=True)
    (root / "final_report_tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {root / 'final_report_tables.md'}")


if __name__ == "__main__":
    main()

