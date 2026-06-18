#!/usr/bin/env python
"""Export SFT/DPO/OPD/RWR/RLVR data from small CodeFixer rollouts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.task_loader import load_yaml
from evaluation.evaluate import run_evaluation
from training.resource_registry import apply_resource_selection


def main() -> None:
    parser = argparse.ArgumentParser(description="Run configured rollouts and export training data.")
    parser.add_argument("--config", default="configs/training_pipeline.yaml")
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-tasks", type=int, default=None)
    args = parser.parse_args()

    config = load_yaml(args.config)
    training = config.get("training", {})
    if training.get("mode", "export_only") != "export_only":
        raise SystemExit("Only training.mode=export_only is supported locally.")

    dataset_name = args.dataset or training.get("dataset") or config.get("resource_selection", {}).get("dataset")
    model_name = args.model or config.get("resource_selection", {}).get("model", "local_rule_based")
    max_tasks = args.max_tasks or int(training.get("max_tasks") or config.get("resource_selection", {}).get("max_tasks", 2))
    config = apply_resource_selection(config, dataset_name=dataset_name, model_name=model_name)

    payload = run_evaluation(
        config_path=args.config,
        overrides=config,
        system_version=config.get("evaluation", {}).get("system_version"),
        max_tasks=max_tasks,
    )
    out_dir = Path(config["paths"].get("training_output_dir", "training"))
    report = {
        "dataset": config["selected_resources"]["dataset_name"],
        "model": config["selected_resources"]["model_name"],
        "max_tasks": max_tasks,
        "metrics": payload["metrics"],
        "training_output_dir": str(out_dir),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "export_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
