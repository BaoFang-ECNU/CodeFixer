"""Task data structures for CodeFixer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """A code repair task loaded from configuration."""

    task_id: str
    issue_path: Path
    source_files: list[Path]
    test_files: list[Path]
    test_command: str
    metadata: dict = field(default_factory=dict)

    def read_issue(self, project_root: Path) -> str:
        """Read the natural language issue text."""

        return (project_root / self.issue_path).read_text(encoding="utf-8")

