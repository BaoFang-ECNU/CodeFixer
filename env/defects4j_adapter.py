"""Defects4J adapter for server-side Java repair evaluation.

The adapter intentionally keeps Defects4J execution behind explicit method
calls so local smoke tests can import and validate it without a Java/Perl/SVN
toolchain. Real checkout, compile, and test commands should run on a Linux
server where Defects4J is installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Defects4JCommandResult:
    """Result from a Defects4J CLI command."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class Defects4JTaskSpec:
    """CodeFixer-compatible metadata for one Defects4J bug."""

    task_id: str
    project: str
    bug_id: int
    issue: str
    workspace: str
    visible_test_command: str
    hidden_test_command: str
    source_files: list[str]
    allowed_files: list[str]
    metadata: dict[str, Any]

    def to_task_config(self, issue_path: str) -> dict[str, Any]:
        """Return a task entry for CodeFixer YAML/JSON configs."""

        return {
            "task_id": self.task_id,
            "language": "java",
            "project_source": "defects4j",
            "construction": "real_bug_checkout",
            "bug_type": "real_java_bug",
            "difficulty": "benchmark",
            "issue": issue_path,
            "source_files": self.source_files,
            "allowed_files": self.allowed_files,
            "test_files": [],
            "hidden_test_files": [],
            "test_command": self.visible_test_command,
            "visible_test_command": self.visible_test_command,
            "hidden_test_command": self.hidden_test_command,
            "metadata": asdict(self),
        }


class Defects4JAdapter:
    """Thin wrapper around the Defects4J command-line interface."""

    def __init__(self, defects4j_bin: str = "defects4j", timeout_sec: int = 600):
        self.defects4j_bin = defects4j_bin
        self.timeout_sec = timeout_sec

    def is_available(self) -> bool:
        """Return whether the defects4j executable is on PATH."""

        return shutil.which(self.defects4j_bin) is not None

    def info(self, project: str) -> Defects4JCommandResult:
        return self._run([self.defects4j_bin, "info", "-p", project])

    def checkout(self, project: str, bug_id: int, workspace: str | Path) -> Defects4JCommandResult:
        return self._run([self.defects4j_bin, "checkout", "-p", project, "-v", f"{bug_id}b", "-w", str(workspace)])

    def compile(self, workspace: str | Path) -> Defects4JCommandResult:
        return self._run([self.defects4j_bin, "compile"], cwd=Path(workspace))

    def test(self, workspace: str | Path) -> Defects4JCommandResult:
        return self._run([self.defects4j_bin, "test"], cwd=Path(workspace))

    def export_property(self, workspace: str | Path, prop: str) -> Defects4JCommandResult:
        return self._run([self.defects4j_bin, "export", "-p", prop], cwd=Path(workspace))

    def build_task_spec(
        self,
        project: str,
        bug_id: int,
        workspace_root: str | Path = "outputs/defects4j_workspaces",
        source_files: list[str] | None = None,
        allowed_files: list[str] | None = None,
    ) -> Defects4JTaskSpec:
        """Create metadata for one Defects4J bug without requiring checkout."""

        task_id = f"defects4j_{project}_{bug_id}"
        workspace = Path(workspace_root) / task_id
        issue = (
            f"Fix Defects4J bug {project}-{bug_id}. "
            "Use Defects4J triggering tests and project tests to validate the patch."
        )
        command = "defects4j test"
        return Defects4JTaskSpec(
            task_id=task_id,
            project=project,
            bug_id=bug_id,
            issue=issue,
            workspace=workspace.as_posix(),
            visible_test_command=command,
            hidden_test_command=command,
            source_files=source_files or [],
            allowed_files=allowed_files or source_files or [],
            metadata={
                "defects4j_project": project,
                "defects4j_bug_id": bug_id,
                "requires_defects4j": True,
                "recommended_setup": ["java11", "git", "svn", "perl", "cpanm"],
            },
        )

    def write_task_config(self, specs: list[Defects4JTaskSpec], config_path: str | Path, issue_dir: str | Path) -> None:
        """Write CodeFixer task config and per-task issue files."""

        issue_root = Path(issue_dir)
        issue_root.mkdir(parents=True, exist_ok=True)
        tasks: list[dict[str, Any]] = []
        for spec in specs:
            issue_path = issue_root / f"{spec.task_id}.md"
            issue_path.write_text(spec.issue + "\n", encoding="utf-8")
            tasks.append(spec.to_task_config(str(issue_path.as_posix())))
        payload = {"tasks": tasks}
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        Path(config_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _run(self, command: list[str], cwd: Path | None = None) -> Defects4JCommandResult:
        try:
            completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=self.timeout_sec, check=False)
            return Defects4JCommandResult(command, completed.returncode, completed.stdout, completed.stderr)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return Defects4JCommandResult(command, 124, stdout, stderr or "timeout")
