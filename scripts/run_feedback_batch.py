#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local +feedback mini-SWE-agent over a manifest slice.")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--candidate-system", default="feedback_candidates")
    parser.add_argument("--selected-system", default="feedback")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--step-limit", type=int, default=1000)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--rerank-only", action="store_true", help="Reuse existing candidates and only redo selection.")
    parser.add_argument("--memory-file", default="", help="Optional evolution memory file passed to each task.")
    parser.add_argument(
        "--prompt-controller",
        choices=["static", "bandit", "contextual_bandit"],
        default="static",
        help="Prompt policy controller passed to each task.",
    )
    parser.add_argument("--bandit-state", default="", help="Optional JSON state path for bandit arm statistics.")
    parser.add_argument("--bandit-seed", type=int, default=0, help="Random seed for Thompson sampling.")
    parser.add_argument(
        "--feedback-root",
        default=str(PROJECT_ROOT / "outputs" / "feedback"),
        help="Directory for per-task feedback reports and feedback prompts.",
    )
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    with Path(args.manifest).open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}
    tasks = manifest.get("tasks", [])[args.start : args.start + args.limit]
    print(f"[feedback-batch] tasks selected: {len(tasks)}")

    failures = 0
    for index, task in enumerate(tasks, start=args.start):
        task_id = str(task["id"])
        print(f"[feedback-batch] ({index}) running {task_id}", flush=True)
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_feedback_task.py"),
            task_id,
            "--manifest",
            args.manifest,
            "--candidate-system",
            args.candidate_system,
            "--selected-system",
            args.selected_system,
            "--attempts",
            str(args.attempts),
            "--step-limit",
            str(args.step_limit),
            "--timeout-sec",
            str(args.timeout_sec),
            "--max-tokens",
            str(args.max_tokens),
            "--prompt-controller",
            args.prompt_controller,
            "--bandit-seed",
            str(args.bandit_seed),
        ]
        if args.rerank_only:
            cmd.append("--rerank-only")
        if args.memory_file:
            cmd.extend(["--memory-file", args.memory_file])
        if args.bandit_state:
            cmd.extend(["--bandit-state", args.bandit_state])
        if args.feedback_root:
            cmd.extend(["--feedback-root", args.feedback_root])
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            failures += 1
            print(f"[feedback-batch] task failed: {task_id} returncode={result.returncode}")
            if not args.continue_on_error:
                return result.returncode

    print(f"[feedback-batch] done. failures={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
