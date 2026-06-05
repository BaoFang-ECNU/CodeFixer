"""Simple self-improving memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Memory:
    """Keep lightweight action statistics and failure notes."""

    def __init__(self):
        self.data: dict[str, Any] = {"action_patterns": {}, "failure_reasons": []}

    def update_pattern(self, name: str, success: bool) -> None:
        pattern = self.data["action_patterns"].setdefault(name, {"success": 0, "failure": 0})
        pattern["success" if success else "failure"] += 1

    def add_failure_reason(self, reason: str) -> None:
        self.data["failure_reasons"].append(reason)

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        if Path(path).exists():
            self.data = json.loads(Path(path).read_text(encoding="utf-8"))

