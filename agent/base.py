"""Base classes shared by CodeFixer agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResult:
    """Summary returned by a repair agent."""

    task_id: str
    success: bool
    final_answer: str
    patch_diff: str
    reward: float
    steps: int
    tool_calls: int
    runtime_sec: float
    patch_size: int
    patch_diff_lines: int
    unsafe_edits: int
    timed_out: bool
    failure_reason: str
    first_pass_step: int | None
    initial_test_output: str
    final_test_output: str
    memory_enabled: bool
    test_feedback_enabled: bool
    trajectory: dict[str, Any]


class BaseAgent:
    """Base interface for project agents."""

    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
