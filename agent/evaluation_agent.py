"""EvaluationAgent wrapper for batch evaluation."""

from __future__ import annotations

from agent.base import BaseAgent
from evaluation.evaluate import run_evaluation


class EvaluationAgent(BaseAgent):
    """Run configured evaluation and return aggregate metrics."""

    def run(self, config_path: str = "configs/default.yaml") -> dict:
        return run_evaluation(config_path)

