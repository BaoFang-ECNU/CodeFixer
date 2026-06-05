"""Adapter for SWE-bench Lite style task metadata.

The adapter keeps the current lightweight `Task` interface while reserving the
fields needed by real SWE-bench instances: repository, base commit, issue text,
test command, and optional file hints.
"""

from __future__ import annotations

from pathlib import Path

from env.task import Task
from env.task_loader import load_yaml


def load_swebench_lite_tasks(tasks_file: str | Path, issue_dir: str | Path = "logs/swebench_issues") -> list[Task]:
    """Load SWE-bench Lite style metadata into CodeFixer Task objects.

    Expected minimal schema per item:
    `instance_id`, `repo`, `base_commit`, `problem_statement`, `test_command`.
    Source files may be unknown at load time, so `file_hints` is optional.
    """

    raw = load_yaml(tasks_file)
    issue_root = Path(issue_dir)
    issue_root.mkdir(parents=True, exist_ok=True)
    tasks: list[Task] = []
    for item in raw.get("tasks", []):
        task_id = item.get("instance_id") or item["task_id"]
        issue_path = issue_root / f"{task_id}.md"
        issue_path.write_text(item.get("problem_statement", ""), encoding="utf-8")
        tasks.append(
            Task(
                task_id=task_id,
                issue_path=issue_path,
                source_files=[Path(p) for p in item.get("file_hints", [])],
                test_files=[],
                test_command=item.get("test_command", "python -m pytest"),
                metadata={
                    "repo": item.get("repo"),
                    "base_commit": item.get("base_commit"),
                    "version": item.get("version", "swebench_lite"),
                    "raw": item,
                },
            )
        )
    return tasks

