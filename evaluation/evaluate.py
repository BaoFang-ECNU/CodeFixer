"""Batch evaluation entrypoint for CodeFixer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent.coding_agent import CodingAgent
from agent.orchestrator import Orchestrator
from env.code_env import CodeRepairEnv
from env.task_loader import load_tasks, load_yaml
from evaluation.metrics import compute_metrics, grouped_metrics, summary_markdown
from training.replay_buffer import ReplayBuffer
from training.policy import build_policy
from training.reward import RewardModel
from training.self_evolution import SelfEvolutionTrainer


def run_evaluation(config_path: str = "configs/default.yaml", overrides: dict[str, Any] | None = None, system_version: str | None = None) -> dict[str, Any]:
    """Run all configured tasks and write results, summary, and trajectories."""

    project_root = Path.cwd()
    config = _load_eval_config(config_path)
    if overrides:
        _deep_update(config, overrides)
    if system_version:
        _apply_system_version(config, system_version)
    system_version = config.get("evaluation", {}).get("system_version", "feedback")
    reward_weights = load_yaml("configs/reward_weights.yaml")
    reward_weights.update(config.get("reward_weights", {}))
    tasks_file = config["paths"]["tasks_file"]
    tasks = load_tasks(project_root / tasks_file)
    logs_dir = project_root / config["paths"]["logs_dir"]
    workspaces_dir = project_root / config["paths"]["workspaces_dir"]
    trajectory_file = project_root / config["paths"]["trajectory_file"]
    results_file = project_root / config["paths"]["results_file"]
    summary_file = project_root / config["paths"]["summary_file"]

    logs_dir.mkdir(parents=True, exist_ok=True)
    workspaces_dir.mkdir(parents=True, exist_ok=True)
    if trajectory_file.exists():
        trajectory_file.unlink()

    results: list[dict[str, Any]] = []
    replay = ReplayBuffer()
    orchestrator = Orchestrator()
    for task in tasks:
        env = CodeRepairEnv(
            task=task,
            project_root=project_root,
            workspaces_dir=workspaces_dir,
            timeout_sec=int(config["environment"]["test_timeout_sec"]),
            unsafe_edit_globs=list(config["environment"].get("unsafe_edit_globs", ["test_*.py"])),
        )
        if config.get("orchestrator", {}).get("mode") == "multi_agent":
            result = orchestrator.run_repair_task(env, reward_weights, trajectory_file, config)
        else:
            agent = CodingAgent(max_steps=int(config["agent"]["max_steps"]), reward_model=RewardModel(reward_weights), policy=build_policy(config))
            result = agent.run(env, trajectory_path=trajectory_file, config=config)
        item = result.__dict__.copy()
        results.append({k: v for k, v in item.items() if k != "trajectory"})
        replay.add(result.trajectory)

    metrics = compute_metrics(results, pass_at_k=int(config["evaluation"]["pass_at_k"]), cost_per_tool_call=float(config["evaluation"]["cost_per_tool_call"]))
    payload = {
        "system_version": system_version,
        "metrics": metrics,
        "grouped_metrics": {
            "by_system_version": grouped_metrics(results, ["system_version"]),
            "by_bug_type": grouped_metrics(results, ["bug_type"]),
            "by_language": grouped_metrics(results, ["language"]),
            "by_project_source": grouped_metrics(results, ["project_source"]),
        },
        "results": results,
    }
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_file.write_text(summary_markdown(metrics, results), encoding="utf-8")
    replay.save_jsonl(project_root / config["paths"]["replay_file"])

    if config["agent"].get("use_self_evolution", True):
        SelfEvolutionTrainer().evolve(replay.items, output_dir=project_root / "training", logs_dir=logs_dir)
    return payload


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _load_eval_config(config_path: str) -> dict[str, Any]:
    config = load_yaml(config_path)
    if "paths" in config:
        return config
    if "tasks" in config:
        base = load_yaml("configs/default.yaml")
        base["paths"]["tasks_file"] = config_path
        return base
    return config


def _apply_system_version(config: dict[str, Any], system_version: str) -> None:
    config.setdefault("evaluation", {})["system_version"] = system_version
    config.setdefault("orchestrator", {})["mode"] = "single_agent"
    if system_version == "baseline":
        config["agent"].update({"use_test_feedback": False, "use_memory": False, "use_self_evolution": False, "max_steps": min(int(config["agent"].get("max_steps", 6)), 3)})
        config["orchestrator"]["mode"] = "single_agent"
    elif system_version == "feedback":
        config["agent"].update({"use_test_feedback": True, "use_memory": False, "use_self_evolution": False})
        config["orchestrator"]["mode"] = "multi_agent"
    elif system_version == "learning":
        config["agent"].update({"use_test_feedback": True, "use_memory": True, "use_self_evolution": True})
        config["orchestrator"]["mode"] = "multi_agent"
    else:
        raise ValueError(f"unknown system version: {system_version}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--system-version", choices=["baseline", "feedback", "learning"], default=None)
    args = parser.parse_args()
    payload = run_evaluation(args.config, system_version=args.system_version)
    print(json.dumps(payload["metrics"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
