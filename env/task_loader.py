"""Load toy or benchmark tasks from YAML configuration."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised only without PyYAML.
    yaml = None

from env.task import Task


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file with a small standard-library friendly wrapper."""

    text = Path(path).read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def load_tasks(tasks_file: str | Path) -> list[Task]:
    """Load all tasks from a YAML file."""

    raw = load_yaml(tasks_file)
    tasks: list[Task] = []
    for item in raw.get("tasks", []):
        tasks.append(
            Task(
                task_id=item["task_id"],
                issue_path=Path(item["issue"]),
                source_files=[Path(p) for p in item.get("source_files", [])],
                test_files=[Path(p) for p in item.get("test_files", [])],
                test_command=item["test_command"],
                language=item.get("language", "python"),
                visible_test_command=item.get("visible_test_command", item.get("test_command")),
                hidden_test_command=item.get("hidden_test_command"),
                project_source=item.get("project_source", "toy"),
                bug_type=item.get("bug_type", "unknown"),
                difficulty=item.get("difficulty", "easy"),
                allowed_files=[Path(p) for p in item.get("allowed_files", item.get("source_files", []))],
                hidden_test_files=[Path(p) for p in item.get("hidden_test_files", [])],
                metadata={k: v for k, v in item.items() if k not in {"task_id", "issue", "source_files", "test_files", "hidden_test_files", "test_command", "visible_test_command", "hidden_test_command", "language", "project_source", "bug_type", "difficulty", "allowed_files"}},
            )
        )
    return tasks
