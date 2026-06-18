#!/usr/bin/env python
"""Run a local mini smoke test using the unified model/dataset registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.task_loader import load_yaml
from evaluation.evaluate import run_evaluation
from training.resource_registry import apply_resource_selection, registry_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tiny local CodeFixer repair test.")
    parser.add_argument("--config", default="configs/local_mini_test.yaml")
    parser.add_argument("--dataset", default=None, help="Dataset key in configs/datasets.yaml.")
    parser.add_argument("--model", default=None, help="Model key in configs/models.yaml.")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--print-registry", action="store_true")
    args = parser.parse_args()

    if args.print_registry:
        print(registry_summary())

    config = load_yaml(args.config)
    config = apply_resource_selection(config, dataset_name=args.dataset, model_name=args.model)
    max_tasks = args.max_tasks or int(config.get("resource_selection", {}).get("max_tasks", 2))
    selected = config["selected_resources"]
    print(
        "[local-mini] dataset={dataset} model={model} max_tasks={max_tasks}".format(
            dataset=selected["dataset_name"],
            model=selected["model_name"],
            max_tasks=max_tasks,
        )
    )

    payload = run_evaluation(config_path=args.config, overrides=config, system_version=config.get("evaluation", {}).get("system_version"), max_tasks=max_tasks)
    out_dir = Path(config["paths"]["results_file"]).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "selected_resources.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"[local-mini] wrote outputs under {out_dir}")


if __name__ == "__main__":
    main()
