"""Interactive code repair environment backed by a temporary workspace."""

from __future__ import annotations

import fnmatch
import shutil
import uuid
from pathlib import Path

from env.patch_manager import PatchManager
from env.task import Task
from env.test_runner import TestResult, TestRunner


class CodeRepairEnv:
    """Expose safe file and test tools for a single code repair task."""

    def __init__(self, task: Task, project_root: Path, workspaces_dir: Path, timeout_sec: int = 20, unsafe_edit_globs: list[str] | None = None):
        self.task = task
        self.project_root = project_root
        self.workspaces_dir = workspaces_dir
        self.workspace = workspaces_dir / f"{task.task_id}_{uuid.uuid4().hex[:8]}"
        self.unsafe_edit_globs = unsafe_edit_globs or ["test_*.py"]
        self.runner = TestRunner(timeout_sec=timeout_sec)
        self.patch_manager: PatchManager | None = None
        self.tool_calls = 0
        self.unsafe_edits = 0
        self.last_test_result: TestResult | None = None

    def reset(self) -> dict:
        """Rebuild the isolated workspace and return the first observation."""

        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        for src in [*self.task.source_files, *self.task.test_files, self.task.issue_path]:
            shutil.copy2(self.project_root / src, self.workspace / Path(src).name)
        self.patch_manager = PatchManager(self.workspace)
        for src in self.task.source_files:
            self.patch_manager.register_file(Path(src).name)
        self.tool_calls = 0
        self.unsafe_edits = 0
        self.last_test_result = None
        return self.observe()

    def observe(self) -> dict:
        """Return the current task observation."""

        issue = (self.workspace / Path(self.task.issue_path).name).read_text(encoding="utf-8")
        source_snapshot = {Path(p).name: (self.workspace / Path(p).name).read_text(encoding="utf-8") for p in self.task.source_files}
        return {
            "task_id": self.task.task_id,
            "issue": issue,
            "source_files": list(source_snapshot.keys()),
            "test_files": [Path(p).name for p in self.task.test_files],
            "source_snapshot": source_snapshot,
            "test_command": self.task.test_command,
            "last_test_output": self.last_test_result.output if self.last_test_result else "",
            "last_test_passed": self.last_test_result.passed if self.last_test_result else False,
            "diff": self.get_diff(count_tool=False),
            "tool_calls": self.tool_calls,
            "unsafe_edits": self.unsafe_edits,
        }

    def inspect_file(self, path: str) -> str:
        self.tool_calls += 1
        return self._safe_path(path).read_text(encoding="utf-8")

    def search_code(self, keyword: str) -> list[dict[str, str | int]]:
        self.tool_calls += 1
        results: list[dict[str, str | int]] = []
        for path in self.workspace.glob("*.py"):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if keyword.lower() in line.lower():
                    results.append({"path": path.name, "line": line_no, "text": line})
        return results

    def edit_file(self, path: str, old_text: str, new_text: str) -> bool:
        self.tool_calls += 1
        rel = Path(path).name
        if self._is_unsafe_edit(rel):
            self.unsafe_edits += 1
            return False
        self._safe_path(rel)
        assert self.patch_manager is not None
        return self.patch_manager.apply_text_edit(rel, old_text, new_text)

    def run_tests(self, command: str | None = None) -> TestResult:
        self.tool_calls += 1
        self.last_test_result = self.runner.run(command or self.task.test_command, cwd=self.workspace)
        return self.last_test_result

    def get_diff(self, count_tool: bool = True) -> str:
        if count_tool:
            self.tool_calls += 1
        assert self.patch_manager is not None
        return self.patch_manager.diff()

    def revert_last_edit(self) -> bool:
        self.tool_calls += 1
        assert self.patch_manager is not None
        return self.patch_manager.revert_last_edit()

    def final_answer(self) -> str:
        self.tool_calls += 1
        status = "passed" if self.last_test_result and self.last_test_result.passed else "not passed"
        return f"Task {self.task.task_id} finished with tests {status}.\n\nPatch:\n{self.get_diff(count_tool=False)}"

    def patch_size(self) -> int:
        assert self.patch_manager is not None
        return self.patch_manager.patch_size()

    def _safe_path(self, path: str | Path) -> Path:
        candidate = (self.workspace / Path(path).name).resolve()
        root = self.workspace.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"unsafe path outside workspace: {path}")
        if not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    def _is_unsafe_edit(self, rel_path: str) -> bool:
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.unsafe_edit_globs)
