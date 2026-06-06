"""Orchestrator for single-agent and multi-agent repair workflows."""

from __future__ import annotations

from agent.algorithm_agent import AlgorithmAgent
from agent.critic_agent import CriticAgent
from agent.diagnosis_agent import DiagnosisAgent
from agent.memory import Memory
from agent.repair_agent import RepairAgent
from agent.research_agent import ResearchAgent


class Orchestrator:
    """Coordinate project agents for reproducible runs."""

    def __init__(self, memory: Memory | None = None):
        self.memory = memory or Memory()
        self.diagnosis_agent = DiagnosisAgent()
        self.repair_agent = RepairAgent()
        self.critic_agent = CriticAgent()

    def run_docs_and_eval(self) -> dict:
        ResearchAgent().run()
        AlgorithmAgent().run()
        from agent.evaluation_agent import EvaluationAgent

        return EvaluationAgent().run()

    def run_repair_task(self, env, reward_weights: dict, trajectory_path, config: dict):
        """Run a diagnose-repair-critic pipeline for one task."""

        initial_observation = env.reset()
        diagnosis = self.diagnosis_agent.run(initial_observation)
        config = {**config, "_diagnosis": diagnosis}
        result = self.repair_agent.run(env, reward_weights, trajectory_path, config, memory=self.memory)
        critic_report = self.critic_agent.run(result.patch_diff, result.__dict__)
        result.critic_report = critic_report
        result.diagnosis = diagnosis
        return result
