"""Replay buffer for successful and failed repair trajectories."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


class ReplayBuffer:
    """Store trajectory summaries for self-evolution."""

    def __init__(self):
        self.items: list[dict[str, Any]] = []

    def add(self, trajectory: dict[str, Any]) -> None:
        self.items.append(trajectory)

    def save_jsonl(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("w", encoding="utf-8") as handle:
            for item in self.items:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def load_jsonl(self, path: str | Path) -> None:
        self.items.clear()
        if not Path(path).exists():
            return
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    self.items.append(json.loads(line))

    def sample_success(self, k: int = 1) -> list[dict[str, Any]]:
        successes = [item for item in self.items if item.get("success")]
        return random.sample(successes, k=min(k, len(successes)))

    def sample_failure(self, k: int = 1) -> list[dict[str, Any]]:
        failures = [item for item in self.items if not item.get("success")]
        return random.sample(failures, k=min(k, len(failures)))

