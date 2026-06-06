"""RepairAgent wraps CodingAgent for multi-agent orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.base import AgentResult, BaseAgent
from agent.coding_agent import CodingAgent
from agent.memory import Memory
from env.code_env import CodeRepairEnv
from training.policy import build_policy
from training.reward import RewardModel


class RepairAgent(BaseAgent):
    """Generate and validate patches using the configured policy."""

    def run(self, env: CodeRepairEnv, reward_weights: dict[str, float], trajectory_path: str | Path, config: dict[str, Any], memory: Memory | None = None) -> AgentResult:
        agent = CodingAgent(
            max_steps=int(config["agent"]["max_steps"]),
            reward_model=RewardModel(reward_weights),
            policy=build_policy(config),
            memory=memory,
        )
        return agent.run(env, trajectory_path=trajectory_path, config=config)

