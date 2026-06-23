#!/usr/bin/env python
from __future__ import annotations

import argparse
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
            for candidate in report.get("candidates", []):
                prompt = semantic_prompt(task, candidate)
                f.write(
                    json.dumps(
                        {
                            "task_id": task_id,
                            "candidate_index": candidate["candidate_index"],
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
    parser = argparse.ArgumentParser(description="Create JSONL prompts for semantic candidate judging.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--feedback-root", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def semantic_prompt(task: dict[str, Any], candidate: dict[str, Any]) -> str:
    issue = str(task.get("issue", ""))
    changed_files = ", ".join(map(str, candidate.get("changed_files", []))) or "NA"
    failure_summary = str(candidate.get("failure_summary") or "NA")
    patch_preview = read_patch(candidate.get("candidate_dir", ""))
    return f"""You are judging a candidate code-repair patch.

Allowed evidence:
- Original issue text.
- Candidate patch diff.
- Candidate visible feedback/failure summary.

Do not assume hidden tests or reference patches.

Return one JSON object only, with integer scores from 0 to 5:
{{
  "fixes_root_cause": 0,
  "minimal_and_targeted": 0,
  "risk_of_regression": 0,
  "test_relevance": 0,
  "reason": "short explanation"
}}

Issue:
{issue}

Changed files:
{changed_files}

Visible feedback / failure summary:
{failure_summary}

Candidate patch:
```diff
{patch_preview}
```
"""


def read_patch(candidate_dir: str) -> str:
    path = Path(candidate_dir) / "patch.diff"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:12000]


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
