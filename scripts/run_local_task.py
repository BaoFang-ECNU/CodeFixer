#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )


def load_task(manifest: Path, task_id: str) -> dict:
    with manifest.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    for task in data.get("tasks", []):
        if str(task.get("id")) == task_id:
            return task
    raise SystemExit(f"Task not found in manifest: {task_id}")


def read_issue(task: dict) -> str:
    issue = str(task.get("issue", ""))
    issue_path = Path(issue)
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8", errors="ignore")
    return issue


def clean_repo(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise SystemExit(f"Repo is not a git checkout: {repo}")
    run(["git", "reset", "--hard"], cwd=repo, check=True)
    run(["git", "clean", "-fd"], cwd=repo, check=True)


def cleanup_agent_artifacts(repo: Path) -> None:
    patterns = [
        "reproduce_issue.py",
        "reproduce_*.py",
        "debug_*.py",
        "*.backup",
        "*.bak",
        "*.orig",
    ]
    for pattern in patterns:
        for path in repo.rglob(pattern):
            if ".git" in path.parts:
                continue
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass


def save_patch(repo: Path, patch_path: Path) -> None:
    cleanup_agent_artifacts(repo)
    # Include newly-created files in the diff without staging their contents.
    run(["git", "add", "-N", "."], cwd=repo)
    diff = run(["git", "diff", "--binary"], cwd=repo, check=True)
    patch_path.write_text(diff.stdout, encoding="utf-8")


def build_prompt(task: dict) -> str:
    visible = task.get("visible_test_command") or "No visible test command is provided. Inspect the repository and use reasonable local checks if possible."
    relevant = task.get("relevant_files") or []
    relevant_text = "\n".join(f"- {path}" for path in relevant) if relevant else "Not provided."
    return f"""You are fixing a local code repair task.

Issue:
{read_issue(task)}

Relevant files from the benchmark metadata:
{relevant_text}

Visible test command:
{visible}

Rules:
- Make the smallest correct code change.
- Avoid printing entire large files. Prefer grep, rg, and sed -n on small line ranges.
- Keep command output short so the context window stays available for reasoning.
- Do not look for or modify hidden tests.
- Do not edit files under tests/ or any test configuration files.
- Do not create backup files such as *.backup, *.bak, or *.orig.
- Stay in the provided repository. Do not clone, copy, or work from another checkout.
- Do not `cd` into `/tmp`, `/home/user`, or any path outside the repository.
- The only allowed `/tmp` path is `/tmp/final.patch` for the final diff file.
- If you create temporary reproduction scripts, remove them before finishing.
- Do not hard-code benchmark answers.
- Only modify source files needed for the fix.
- Run available checks when useful.
- Before finishing, remove temporary files and inspect the final diff.

Mandatory patch submission protocol:
- Your final submitted output must be only a valid unified git diff, not a summary.
- The final patch must be generated from the working tree with `git diff --binary`.
- Verify the final patch with `git apply --check` before finishing.
- Do not include Markdown fences, bullet lists, explanations, or natural language in the final patch output.
- The first non-empty patch line must look like `diff --git a/path b/path`.
- If there is no valid source-code fix, leave an empty patch rather than submitting a natural-language explanation.
- Finish by issuing `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat /tmp/final.patch` after creating and verifying `/tmp/final.patch`.
"""


def append_feedback(prompt: str, feedback_path: Path | None) -> str:
    if not feedback_path:
        return prompt
    if not feedback_path.exists():
        raise SystemExit(f"Feedback file not found: {feedback_path}")
    feedback = feedback_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not feedback:
        return prompt
    return (
        prompt
        + "\n\nFeedback from previous candidate attempts:\n"
        + feedback
        + "\n\nUse this feedback to produce a cleaner source-only patch. Do not mention the feedback in the final patch.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run vanilla mini-SWE-agent on one local SWE-bench-derived task.")
    parser.add_argument("task_id")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--system", default="baseline")
    parser.add_argument("--candidate", type=int, default=0)
    parser.add_argument("--model", default="hosted_vllm/qwen3-coder-30b-a3b")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--step-limit", type=int, default=80)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--feedback-file", default="", help="Optional feedback summary to append to the task prompt.")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    task = load_task(manifest, args.task_id)
    repo = Path(task["repo_path"])
    if not repo.is_absolute():
        repo = (PROJECT_ROOT / repo).resolve()

    out_dir = PROJECT_ROOT / "outputs" / "local_runs" / args.system / args.task_id / f"candidate_{args.candidate}"
    out_dir.mkdir(parents=True, exist_ok=True)
    patch_path = out_dir / "patch.diff"
    traj_path = out_dir / "trajectory.json"
    metadata_path = out_dir / "metadata.json"
    prompt_path = out_dir / "prompt.txt"
    feedback_path = Path(args.feedback_file) if args.feedback_file else None
    prompt = append_feedback(build_prompt(task), feedback_path)
    prompt_path.write_text(prompt, encoding="utf-8")

    clean_repo(repo)

    env = os.environ.copy()
    env.setdefault("MSWEA_MODEL_NAME", args.model)
    env.setdefault("MSWEA_MODEL_API_KEY_NAME", "OPENAI_API_KEY")
    env.setdefault("OPENAI_API_KEY", "dummy")
    env.setdefault("LITELLM_MODEL_REGISTRY_PATH", str(PROJECT_ROOT / "configs" / "litellm_registry.json"))
    env.setdefault("MSWEA_COST_TRACKING", "ignore_errors")
    env.setdefault("PAGER", "cat")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("TQDM_DISABLE", "1")

    cmd = [
        "mini",
        "--yolo",
        "--cost-limit",
        "0",
        "--model",
        args.model,
        "--config",
        "mini.yaml",
        "--config",
        str(PROJECT_ROOT / "configs" / "qwen3_vllm_mini_swe.yaml"),
        "--config",
        f"agent.step_limit={args.step_limit}",
        "--config",
        f"model.model_kwargs.max_tokens={args.max_tokens}",
        "--config",
        f"environment.cwd={repo}",
        "--environment-class",
        "local",
        "--output",
        str(traj_path),
        "--task",
        prompt,
    ]

    start = time.monotonic()
    log_path = out_dir / "mini_stdout.log"
    returncode = 0
    with log_path.open("w", encoding="utf-8", errors="ignore") as log:
        log.write("[local-task] command:\n")
        log.write(" ".join(cmd) + "\n\n")
        log.write("[local-task] stdin: one newline is preloaded so mini can exit its final prompt in batch mode.\n\n")
        log.flush()
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        if process.stdin is not None:
            process.stdin.write("\n")
            process.stdin.close()
        deadline = start + args.timeout_sec
        assert process.stdout is not None
        while True:
            line = process.stdout.readline()
            if line:
                print(line, end="")
                log.write(line)
                log.flush()
            if process.poll() is not None:
                remainder = process.stdout.read()
                if remainder:
                    print(remainder, end="")
                    log.write(remainder)
                returncode = process.returncode
                break
            if time.monotonic() > deadline:
                process.kill()
                returncode = 124
                message = f"\n[local-task] timed out after {args.timeout_sec} seconds\n"
                print(message, end="")
                log.write(message)
                break

    save_patch(repo, patch_path)
    wall_time = round(time.monotonic() - start, 4)

    metadata = {
        "task_id": args.task_id,
        "system": args.system,
        "candidate": args.candidate,
        "returncode": returncode,
        "wall_time_sec": wall_time,
        "cost": 0.0,
        "step_limit": args.step_limit,
        "max_tokens": args.max_tokens,
        "feedback_file": str(feedback_path) if feedback_path else "",
        "notes": "vanilla mini-SWE-agent local baseline",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    clean_repo(repo)
    print(f"[local-task] task={args.task_id} returncode={returncode}")
    print(f"[local-task] patch={patch_path}")
    print(f"[local-task] trajectory={traj_path}")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
