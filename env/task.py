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
    language: str = "python"
    visible_test_command: str | None = None
    hidden_test_command: str | None = None
    project_source: str = "toy"
    bug_type: str = "unknown"
    difficulty: str = "easy"
    allowed_files: list[Path] = field(default_factory=list)
    hidden_test_files: list[Path] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def visible_command(self) -> str:
        """Return the visible test command, keeping backward compatibility."""

        return self.visible_test_command or self.test_command

    def hidden_command(self) -> str | None:
        """Return the hidden/regression test command when configured."""

        return self.hidden_test_command

    def read_issue(self, project_root: Path) -> str:
        """Read the natural language issue text."""

        return (project_root / self.issue_path).read_text(encoding="utf-8")
