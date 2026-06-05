"""Small orchestrator for research, algorithm, coding, and evaluation agents."""

from __future__ import annotations

from agent.algorithm_agent import AlgorithmAgent
from agent.evaluation_agent import EvaluationAgent
from agent.research_agent import ResearchAgent


class Orchestrator:
    """Coordinate project agents for reproducible runs."""

    def run_docs_and_eval(self) -> dict:
        ResearchAgent().run()
        AlgorithmAgent().run()
        return EvaluationAgent().run()

