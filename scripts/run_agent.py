"""Run CodeFixer on the first configured toy task."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.coding_agent import CodingAgent
from env.code_env import CodeRepairEnv
from env.task_loader import load_tasks, load_yaml
from training.policy import build_policy
from training.reward import RewardModel


def main() -> None:
    root = Path.cwd()
    config = load_yaml(root / "configs/default.yaml")
    reward_weights = load_yaml(root / "configs/reward_weights.yaml")
    task = load_tasks(root / config["paths"]["tasks_file"])[0]
    env = CodeRepairEnv(
        task=task,
        project_root=root,
        workspaces_dir=root / config["paths"]["workspaces_dir"],
        timeout_sec=int(config["environment"]["test_timeout_sec"]),
        unsafe_edit_globs=list(config["environment"].get("unsafe_edit_globs", ["test_*.py"])),
    )
    agent = CodingAgent(max_steps=int(config["agent"]["max_steps"]), reward_model=RewardModel(reward_weights), policy=build_policy(config))
    result = agent.run(env, trajectory_path=root / config["paths"]["trajectory_file"], config=config)
    print(json.dumps({k: v for k, v in result.__dict__.items() if k != "trajectory"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
