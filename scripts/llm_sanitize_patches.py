#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


VALID_DIFF_HEADER = re.compile(r"^diff --git a/.+ b/.+$", re.M)
FENCE_START = re.compile(r"^```(?:diff|patch)?\s*", re.I)
FENCE_END = re.compile(r"\s*```$", re.I)

DEFAULT_BAD_FILE_PATTERNS = [
    r"(^|/)tests?/",
    r"(^|/)test_.*\.py$",
    r"(^|/).*_test\.py$",
    r"(^|/)conftest\.py$",
    r"(^|/)pytest\.ini$",
    r"(^|/)tox\.ini$",
    r"(^|/)test_app/",
    r"(^|/)test_reproduction/",
    r"(^|/)settings\.py$",
    r"(^|/)test_settings\.py$",
    r"(^|/)manage\.py$",
    r"(^|/)models\.py$",
    r"(^|/)reproduce.*\.py$",
    r"(^|/)debug.*\.py$",
    r"(^|/)tmp.*",
    r"\.bak$",
    r"\.backup$",
    r"\.orig$",
]

BENCHMARK_ARTIFACT_HINTS = [
    "hidden_test.patch",
    "reference.patch",
    "record.json",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
]

PROMPT_TEMPLATE = """You are a patch-format sanitizer for SWE-bench submissions.

Your input is a candidate patch or an invalid patch-like answer produced by a code repair agent.

Rewrite it into a valid unified git diff suitable for SWE-bench submission.

Rules:
- Preserve only real source-code changes already present in the candidate patch.
- Remove explanations, Markdown fences, summaries, bullet lists, and prose.
- Remove temporary reproduction files, scratch files, backup files, standalone test scripts, and benchmark artifacts.
- Remove changes to tests, test configuration, hidden tests, reference patches, record files, and generated files.
- Do not invent new code changes.
- Do not improve or rewrite the repair logic.
- Do not use hidden tests or reference solutions.
- If no valid source-code diff remains, output an empty string.
- Output only the final unified git diff. The first non-empty line, if any, must be: diff --git a/... b/...

Candidate patch:
```diff
{patch}
```
"""


def changed_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[2].startswith("a/") and parts[3].startswith("b/"):
            files.append(parts[3][2:])
    return sorted(set(files))


def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = FENCE_START.sub("", text)
    text = FENCE_END.sub("", text)
    return text.strip() + ("\n" if text.strip() else "")


def is_malformed_patch(patch: str) -> bool:
    return bool(patch.strip()) and not bool(VALID_DIFF_HEADER.search(patch))


def has_benchmark_artifact_content(text: str) -> bool:
    return any(hint in text for hint in BENCHMARK_ARTIFACT_HINTS)


def suspicious_files(files: list[str], patterns: list[re.Pattern[str]]) -> list[str]:
    bad: list[str] = []
    for path in files:
        posix = Path(path).as_posix()
        if any(pattern.search(posix) for pattern in patterns):
            bad.append(path)
    return bad


def call_vllm(prompt: str, api_base: str, model: str, max_tokens: int, timeout_sec: int) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"])


def make_row(instance_id: str, before: str, after: str, status: str, notes: str, changed: bool) -> dict[str, Any]:
    before_files = changed_files(before)
    after_files = changed_files(after)
    return {
        "instance_id": instance_id,
        "status": status,
        "changed": changed,
        "before_chars": len(before),
        "after_chars": len(after),
        "before_files": len(before_files),
        "after_files": len(after_files),
        "before_empty": not bool(before.strip()),
        "after_empty": not bool(after.strip()),
        "before_malformed": is_malformed_patch(before),
        "after_malformed": is_malformed_patch(after),
        "after_files_list": ";".join(after_files),
        "notes": notes,
    }


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "instance_id",
        "status",
        "changed",
        "before_chars",
        "after_chars",
        "before_files",
        "after_files",
        "before_empty",
        "after_empty",
        "before_malformed",
        "after_malformed",
        "after_files_list",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sanitize_one(
    patch_path: Path,
    api_base: str,
    model: str,
    max_tokens: int,
    timeout_sec: int,
    prompt_patch_char_limit: int,
    bad_file_patterns: list[re.Pattern[str]],
    dry_run: bool,
) -> dict[str, Any]:
    instance_id = patch_path.parents[1].name
    before = patch_path.read_text(encoding="utf-8", errors="ignore")
    if not before.strip():
        return make_row(instance_id, before, before, "skipped_empty", "", False)

    prompt = PROMPT_TEMPLATE.format(patch=before[:prompt_patch_char_limit])
    try:
        model_output = call_vllm(prompt, api_base, model, max_tokens, timeout_sec)
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return make_row(instance_id, before, before, "error", str(exc), False)

    after = strip_markdown_fences(model_output)
    after_files = changed_files(after)
    bad_files = suspicious_files(after_files, bad_file_patterns)
    notes: list[str] = []
    if bad_files:
        notes.append("suspicious_files=" + ";".join(bad_files))
    if has_benchmark_artifact_content(after):
        notes.append("benchmark_artifact_hint")

    backup_path = patch_path.with_suffix(".diff.raw_before_llm_sanitize")
    if not dry_run:
        if not backup_path.exists():
            backup_path.write_text(before, encoding="utf-8")
        patch_path.write_text(after, encoding="utf-8")

    return make_row(instance_id, before, after, "sanitized", ";".join(notes), before != after)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sanitize candidate patch.diff files with a local OpenAI-compatible LLM. "
            "This is a submission-formatting pass: it should remove prose, tests, and artifacts without inventing repairs."
        )
    )
    parser.add_argument("--runs-dir", required=True, help="Directory like outputs/local_runs/<system>")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001/v1", help="OpenAI-compatible API base")
    parser.add_argument("--model", default="qwen3-coder-30b-a3b", help="Served model name")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--prompt-patch-char-limit", type=int, default=60000)
    parser.add_argument("--only-task", action="append", default=[], help="Only sanitize this task id; can be repeated")
    parser.add_argument("--report-csv", default="", help="Optional CSV report path")
    parser.add_argument("--dry-run", action="store_true", help="Call the LLM and report changes without writing patch.diff")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.runs_dir)
    if not root.exists():
        raise SystemExit(f"runs dir does not exist: {root}")

    task_filter = set(args.only_task)
    bad_file_patterns = [re.compile(pattern) for pattern in DEFAULT_BAD_FILE_PATTERNS]
    patch_paths = sorted(root.glob("*/candidate_0/patch.diff"))
    rows: list[dict[str, Any]] = []

    for patch_path in patch_paths:
        instance_id = patch_path.parents[1].name
        if task_filter and instance_id not in task_filter:
            continue
        row = sanitize_one(
            patch_path=patch_path,
            api_base=args.api_base,
            model=args.model,
            max_tokens=args.max_tokens,
            timeout_sec=args.timeout_sec,
            prompt_patch_char_limit=args.prompt_patch_char_limit,
            bad_file_patterns=bad_file_patterns,
            dry_run=args.dry_run,
        )
        rows.append(row)
        print(
            f"{row['instance_id']}: {row['status']} "
            f"{row['before_chars']} -> {row['after_chars']} chars "
            f"changed={row['changed']}"
        )
        if row["notes"]:
            print(f"  notes: {row['notes']}")

    changed = sum(1 for row in rows if row["changed"])
    errors = sum(1 for row in rows if row["status"] == "error")
    after_empty = sum(1 for row in rows if row["after_empty"])
    after_malformed = sum(1 for row in rows if row["after_malformed"])
    print(f"\nprocessed: {len(rows)}")
    print(f"changed: {changed}")
    print(f"errors: {errors}")
    print(f"after_empty: {after_empty}")
    print(f"after_malformed: {after_malformed}")

    if args.report_csv:
        write_report(Path(args.report_csv), rows)
        print(f"wrote report: {args.report_csv}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
