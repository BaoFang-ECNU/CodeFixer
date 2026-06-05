"""Reward model for code repair trajectories."""

from __future__ import annotations

from dataclasses import dataclass

from env.test_runner import TestResult


@dataclass
class RewardBreakdown:
    """Reward components for explainable evaluation."""

    total: float
    passed: bool
    patch_size: int
    tool_calls: int
    unsafe_edits: int
    timed_out: bool
    improved: bool


class RewardModel:
    """Compute rewards from tests, patch size, costs, and safety signals."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or {}

    def score(
        self,
        test_result: TestResult | None,
        patch_size: int,
        tool_calls: int,
        unsafe_edits: int,
        previous_failed: bool = True,
    ) -> RewardBreakdown:
        passed = bool(test_result and test_result.passed)
        timed_out = bool(test_result and test_result.timed_out)
        improved = passed and previous_failed
        total = 0.0
        total += self.weights.get("pass_visible_tests", 1.0) if passed else 0.0
        total += self.weights.get("test_improvement", 0.25) if improved else 0.0
        total += self.weights.get("patch_size_penalty", -0.02) * patch_size
        total += self.weights.get("tool_call_penalty", -0.03) * tool_calls
        total += self.weights.get("unsafe_edit_penalty", -1.0) * unsafe_edits
        total += self.weights.get("timeout_penalty", -0.5) if timed_out else 0.0
        if test_result and not passed and not improved:
            total += self.weights.get("no_progress_penalty", -0.15)
        return RewardBreakdown(
            total=round(total, 4),
            passed=passed,
            patch_size=patch_size,
            tool_calls=tool_calls,
            unsafe_edits=unsafe_edits,
            timed_out=timed_out,
            improved=improved,
        )

