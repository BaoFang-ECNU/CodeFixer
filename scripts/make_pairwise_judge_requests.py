#!/usr/bin/env python
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = parse_args()
    manifest = yaml.safe_load(resolve_path(args.manifest).read_text(encoding="utf-8"))
    tasks = manifest["tasks"][args.start : args.start + args.limit if args.limit else None]
    tasks_by_id = {str(task["id"]): task for task in tasks}
    feedback_root = resolve_path(args.feedback_root)
    output = resolve_path(args.output_jsonl)
    output.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with output.open("w", encoding="utf-8") as f:
        for task_id, task in tasks_by_id.items():
            report_path = feedback_root / task_id / "feedback_report.json"
            if not report_path.exists():
                continue
            report = json.loads(report_path.read_text(encoding="utf-8"))
            candidates = list(report.get("candidates", []))
            for left, right in itertools.combinations(candidates, 2):
                prompt = pairwise_prompt(task, left, right)
                f.write(
                    json.dumps(
                        {
                            "task_id": task_id,
                            "candidate_a": left["candidate_index"],
                            "candidate_b": right["candidate_index"],
                            "prompt": prompt,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                written += 1
    print(f"wrote: {output}")
    print(f"requests: {written}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create JSONL prompts for pairwise candidate judging.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--feedback-root", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def pairwise_prompt(task: dict[str, Any], candidate_a: dict[str, Any], candidate_b: dict[str, Any]) -> str:
    issue = str(task.get("issue", ""))
    return f"""You are comparing two candidate patches for the same code-repair task.

Choose the candidate more likely to fix the original issue without causing regressions.
Use only the issue text, candidate diffs, changed files, and visible feedback.
Do not use hidden tests, official results, or reference patches.

Return one JSON object only:
{{
  "winner": "A",
  "confidence": 0.0,
  "reason": "short explanation"
}}

Issue:
{issue}

Candidate A changed files:
{", ".join(map(str, candidate_a.get("changed_files", []))) or "NA"}

Candidate A visible feedback:
{candidate_a.get("failure_summary") or "NA"}

Candidate A patch:
```diff
{read_patch(candidate_a.get("candidate_dir", ""))}
```

Candidate B changed files:
{", ".join(map(str, candidate_b.get("changed_files", []))) or "NA"}

Candidate B visible feedback:
{candidate_b.get("failure_summary") or "NA"}

Candidate B patch:
```diff
{read_patch(candidate_b.get("candidate_dir", ""))}
```
"""


def read_patch(candidate_dir: str) -> str:
    path = Path(candidate_dir) / "patch.diff"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:9000]


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
