from pathlib import Path

from agent.orchestrator import Orchestrator
from env.code_env import CodeRepairEnv
from env.task_loader import load_tasks, load_yaml


def test_multi_agent_orchestrator_repairs_toy_task(tmp_path):
    root = Path.cwd()
    task = load_tasks(root / "configs/tasks_toy.yaml")[0]
    env = CodeRepairEnv(task, root, tmp_path)
    config = load_yaml(root / "configs/default.yaml")
    config["orchestrator"] = {"mode": "multi_agent"}
    result = Orchestrator().run_repair_task(env, load_yaml(root / "configs/reward_weights.yaml"), tmp_path / "traj.jsonl", config)
    assert result.success
    assert result.diagnosis is not None
    assert result.critic_report is not None

