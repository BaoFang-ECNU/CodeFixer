#!/usr/bin/env python
"""Prepare SWE-bench Lite style task configs for CodeFixer.

This script works offline with the bundled sample config. On a server with the
`datasets` package and dataset access, it can also read Princeton SWE-bench
Lite metadata from Hugging Face.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.task_loader import load_yaml


def load_instances(source: str, split: str, max_instances: int) -> list[dict[str, Any]]:
    if source == "sample":
        return load_yaml("configs/tasks_swebench_sample.yaml").get("tasks", [])[:max_instances]
    try:
        from datasets import load_dataset  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("Install `datasets` on the server or use --source sample.") from exc
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split=split)
    rows: list[dict[str, Any]] = []
    for item in dataset.select(range(min(max_instances, len(dataset)))):
        rows.append(
            {
                "instance_id": item.get("instance_id"),
                "repo": item.get("repo"),
                "base_commit": item.get("base_commit"),
                "problem_statement": item.get("problem_statement", ""),
                "file_hints": [],
                "test_command": "python -m pytest",
                "language": "python",
                "metadata": {"patch": item.get("patch"), "test_patch": item.get("test_patch")},
            }
        )
    return rows


def to_codefixer_tasks(instances: list[dict[str, Any]], issue_dir: str | Path) -> list[dict[str, Any]]:
    issue_root = Path(issue_dir)
    issue_root.mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(instances, start=1):
        task_id = item.get("instance_id") or item.get("task_id") or f"swebench_lite_{index:04d}"
        issue_path = issue_root / f"{task_id}.md"
        issue_path.write_text(item.get("problem_statement", ""), encoding="utf-8")
        tasks.append(
            {
                "task_id": task_id,
                "language": item.get("language", "python"),
                "project_source": item.get("repo", "swebench_lite"),
                "construction": "swebench_lite",
                "bug_type": item.get("bug_type", "real_repo_bug"),
                "difficulty": item.get("difficulty", "benchmark"),
                "issue": issue_path.as_posix(),
                "source_files": item.get("file_hints", []),
                "allowed_files": item.get("file_hints", []),
                "test_files": [],
                "hidden_test_files": [],
                "test_command": item.get("test_command", "python -m pytest"),
                "visible_test_command": item.get("test_command", "python -m pytest"),
                "hidden_test_command": item.get("hidden_test_command"),
                "metadata": {
                    "repo": item.get("repo"),
                    "base_commit": item.get("base_commit"),
                    "raw": item,
                    "requires_repo_checkout": True,
                },
            }
        )
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a SWE-bench Lite CodeFixer config.")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-instances", type=int, default=50)
    parser.add_argument("--source", choices=["sample", "hf"], default="sample")
    parser.add_argument("--output", default="configs/tasks_swebench_lite_train.yaml")
    parser.add_argument("--issue-dir", default="examples/swebench_lite_tasks")
    args = parser.parse_args()

    instances = load_instances(args.source, args.split, args.max_instances)
    payload = {"tasks": to_codefixer_tasks(instances, args.issue_dir)}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": args.output,
                "split": args.split,
                "source": args.source,
                "num_instances": len(instances),
                "next_step": "python scripts/export_training_data.py --config configs/training_pipeline_swebench.yaml",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
