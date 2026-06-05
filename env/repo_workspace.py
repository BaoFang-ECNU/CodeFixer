"""Repository workspace manager for future real-issue benchmarks."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    """Result from a repository command."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class RepoWorkspace:
    """Manage clone, checkout, diff, and patch operations for real repositories."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def clone(self, repo_url: str, name: str) -> CommandResult:
        target = self.root / name
        if target.exists():
            return CommandResult(["git", "clone", repo_url, str(target)], 0, f"reuse existing {target}", "")
        return self._run(["git", "clone", repo_url, str(target)], cwd=self.root)

    def checkout(self, repo_path: str | Path, commit: str) -> CommandResult:
        return self._run(["git", "checkout", commit], cwd=Path(repo_path))

    def diff(self, repo_path: str | Path) -> str:
        return self._run(["git", "diff"], cwd=Path(repo_path)).stdout

    def apply_patch(self, repo_path: str | Path, patch_file: str | Path) -> CommandResult:
        return self._run(["git", "apply", str(Path(patch_file).resolve())], cwd=Path(repo_path))

    @staticmethod
    def _run(command: list[str], cwd: Path) -> CommandResult:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)

