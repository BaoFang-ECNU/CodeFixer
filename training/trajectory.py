"""Trajectory records for multi-step code repair."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return an ISO timestamp."""

    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrajectoryStep:
    """One observation-action-feedback record."""

    task_id: str
    step_id: int
    observation: dict[str, Any]
    action: str
    action_args: dict[str, Any]
    test_output: str
    reward: float
    done: bool
    patch_diff: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Trajectory:
    """A sequence of repair steps for one task."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.steps: list[TrajectoryStep] = []

    def add(self, step: TrajectoryStep) -> None:
        self.steps.append(step)

    @property
    def success(self) -> bool:
        return bool(self.steps and self.steps[-1].done)

    @property
    def total_reward(self) -> float:
        return sum(step.reward for step in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "success": self.success, "total_reward": self.total_reward, "steps": [step.to_dict() for step in self.steps]}

    def save_jsonl(self, path: str | Path, append: bool = True) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with Path(path).open(mode, encoding="utf-8") as handle:
            for step in self.steps:
                handle.write(json.dumps(step.to_dict(), ensure_ascii=False) + "\n")

