#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local mini-SWE-agent baseline over tasks in a manifest.")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--system", default="baseline")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--step-limit", type=int, default=80)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    with Path(args.manifest).open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}
    tasks = manifest.get("tasks", [])[args.start : args.start + args.limit]
    print(f"[local-batch] tasks selected: {len(tasks)}")

    failures = 0
    for index, task in enumerate(tasks, start=args.start):
        task_id = str(task["id"])
        print(f"[local-batch] ({index}) running {task_id}")
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_local_task.py"),
                task_id,
                "--manifest",
                args.manifest,
                "--system",
                args.system,
                "--step-limit",
                str(args.step_limit),
                "--timeout-sec",
                str(args.timeout_sec),
                "--max-tokens",
                str(args.max_tokens),
            ],
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            failures += 1
            print(f"[local-batch] task failed: {task_id} returncode={result.returncode}")
            if not args.continue_on_error:
                return result.returncode

    print(f"[local-batch] done. failures={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
