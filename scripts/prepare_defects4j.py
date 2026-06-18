#!/usr/bin/env python
"""Prepare Defects4J task metadata for CodeFixer final evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.defects4j_adapter import Defects4JAdapter


def parse_projects(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create CodeFixer configs for Defects4J evaluation.")
    parser.add_argument("--projects", default="Lang,Chart,Math", help="Comma-separated Defects4J project ids.")
    parser.add_argument("--max-bugs", type=int, default=10, help="Total number of bug specs to generate.")
    parser.add_argument("--bugs-per-project", type=int, default=5)
    parser.add_argument("--defects4j-bin", default="defects4j")
    parser.add_argument("--output", default="configs/tasks_defects4j.yaml")
    parser.add_argument("--issue-dir", default="examples/defects4j_tasks")
    parser.add_argument("--workspace-root", default="outputs/defects4j_workspaces")
    parser.add_argument("--check-env", action="store_true", help="Also check whether defects4j is on PATH.")
    parser.add_argument("--checkout", action="store_true", help="Checkout generated bugs. Intended for Linux servers only.")
    args = parser.parse_args()

    adapter = Defects4JAdapter(defects4j_bin=args.defects4j_bin)
    projects = parse_projects(args.projects)
    specs = []
    for project in projects:
        for bug_id in range(1, args.bugs_per_project + 1):
            if len(specs) >= args.max_bugs:
                break
            specs.append(adapter.build_task_spec(project, bug_id, workspace_root=args.workspace_root))
        if len(specs) >= args.max_bugs:
            break

    adapter.write_task_config(specs, args.output, args.issue_dir)

    checkout_results = []
    if args.checkout:
        for spec in specs:
            result = adapter.checkout(spec.project, spec.bug_id, spec.workspace)
            checkout_results.append({"task_id": spec.task_id, "returncode": result.returncode, "stderr": result.stderr})

    report = {
        "output": args.output,
        "issue_dir": args.issue_dir,
        "num_tasks": len(specs),
        "defects4j_available": adapter.is_available() if args.check_env or args.checkout else None,
        "checkout_requested": args.checkout,
        "checkout_results": checkout_results,
        "next_step": "python -m evaluation.evaluate --config configs/defects4j_eval.yaml --max-tasks 10",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

