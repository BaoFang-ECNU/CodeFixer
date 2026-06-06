"""EvolutionAgent updates long-term memory from repair trajectories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.base import BaseAgent
from agent.memory import Memory
from training.self_evolution import SelfEvolutionTrainer


class EvolutionAgent(BaseAgent):
    """Run self-evolution and persist memory artifacts."""

    def __init__(self, memory: Memory | None = None):
        self.memory = memory or Memory()

    def run(self, trajectories: list[dict[str, Any]], output_dir: str | Path = "training", logs_dir: str | Path = "logs") -> dict[str, Any]:
        trainer = SelfEvolutionTrainer(self.memory)
        return trainer.evolve(trajectories, output_dir=output_dir, logs_dir=logs_dir)

