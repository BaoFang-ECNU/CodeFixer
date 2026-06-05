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
                metadata={k: v for k, v in item.items() if k not in {"task_id", "issue", "source_files", "test_files", "test_command"}},
            )
        )
    return tasks
