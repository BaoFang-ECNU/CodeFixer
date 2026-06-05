"""Patch, diff, and rollback helpers for repair workspaces."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EditRecord:
    """A reversible text edit."""

    path: Path
    before: str
    after: str


class PatchManager:
    """Track original files and reversible edits."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.originals: dict[Path, str] = {}
        self.edits: list[EditRecord] = []

    def register_file(self, rel_path: str | Path) -> None:
        path = self.workspace / rel_path
        rel = Path(rel_path)
        if rel not in self.originals:
            self.originals[rel] = path.read_text(encoding="utf-8")

    def apply_text_edit(self, rel_path: str | Path, old_text: str, new_text: str) -> bool:
        rel = Path(rel_path)
        path = self.workspace / rel
        self.register_file(rel)
        before = path.read_text(encoding="utf-8")
        if old_text not in before:
            return False
        after = before.replace(old_text, new_text, 1)
        path.write_text(after, encoding="utf-8")
        self.edits.append(EditRecord(path=rel, before=before, after=after))
        return True

    def revert_last_edit(self) -> bool:
        if not self.edits:
            return False
        edit = self.edits.pop()
        (self.workspace / edit.path).write_text(edit.before, encoding="utf-8")
        return True

    def diff(self) -> str:
        chunks: list[str] = []
        for rel, original in sorted(self.originals.items(), key=lambda item: str(item[0])):
            current = (self.workspace / rel).read_text(encoding="utf-8")
            if current == original:
                continue
            chunks.extend(
                difflib.unified_diff(
                    original.splitlines(),
                    current.splitlines(),
                    fromfile=f"a/{rel.as_posix()}",
                    tofile=f"b/{rel.as_posix()}",
                    lineterm="",
                )
            )
        return "\n".join(chunks)

    def patch_size(self) -> int:
        diff = self.diff()
        return sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))

