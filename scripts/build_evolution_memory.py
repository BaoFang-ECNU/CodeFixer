#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_reports(feedback_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(feedback_dir.glob("*/feedback_report.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            reports.append(data)
    return reports


def count_issue_flags(reports: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for report in reports:
        for row in report.get("candidates", []):
            if row.get("empty_patch"):
                counts["empty_patch"] += 1
            if row.get("malformed_patch"):
                counts["malformed_patch"] += 1
            if row.get("test_file_edit"):
                counts["test_file_edit"] += 1
            if row.get("artifact_file_edit"):
                counts["artifact_file_edit"] += 1
            if row.get("unsafe_edit"):
                counts["unsafe_edit"] += 1
            if row.get("workdir_drift"):
                counts["workdir_drift"] += 1
            if row.get("benchmark_artifact_exposure"):
                counts["benchmark_artifact_exposure"] += 1
            if row.get("benchmark_artifact_content_access"):
                counts["benchmark_artifact_content_access"] += 1
            if not row.get("patch_apply"):
                counts["patch_apply_failed"] += 1
            if row.get("visible_pass") is False:
                counts["visible_failed"] += 1
            if int(row.get("patch_lines") or 0) > 300:
                counts["large_patch"] += 1
            if int(row.get("patch_files") or 0) > 5:
                counts["many_files"] += 1
    return counts


def collect_good_files(reports: list[dict[str, Any]]) -> Counter[str]:
    files: Counter[str] = Counter()
    for report in reports:
        best = report.get("best", {})
        if not best.get("patch_apply"):
            continue
        if not best.get("submission_compliant"):
            continue
        if best.get("visible_pass") is False:
            continue
        for path in best.get("changed_files", []):
            files[str(path)] += 1
    return files


def build_memory(reports: list[dict[str, Any]]) -> str:
    issue_counts = count_issue_flags(reports)
    good_files = collect_good_files(reports)
    total_tasks = len(reports)
    total_candidates = sum(len(report.get("candidates", [])) for report in reports)
    selected_compliant = sum(1 for report in reports if report.get("best", {}).get("selection_compliant"))
    selected_apply = sum(1 for report in reports if report.get("best", {}).get("patch_apply"))

    lines: list[str] = [
        "Evolution memory for the next CodeFixer feedback run.",
        "",
        "Scope and safety:",
        "- This memory is derived only from previous candidate trajectories, patch-compliance checks, patch-apply checks, and visible-test feedback.",
        "- Do not use reference patches, hidden tests, official verdicts, or benchmark artifact contents.",
        "- Treat this memory as process guidance, not as task-specific answers.",
        "",
        "Aggregate observations:",
        f"- Previous tasks with feedback reports: {total_tasks}",
        f"- Previous candidate patches inspected: {total_candidates}",
        f"- Selected candidates that applied cleanly: {selected_apply}",
        f"- Selected candidates that were selection-compliant: {selected_compliant}",
    ]

    if issue_counts:
        lines.extend(["", "Frequent failure modes to avoid:"])
        for name, count in issue_counts.most_common():
            lines.append(f"- {name}: {count}")

    if good_files:
        lines.extend(["", "Source-file patterns that appeared in compliant selected patches:"])
        for path, count in good_files.most_common(20):
            lines.append(f"- {path}: {count}")

    lines.extend(
        [
            "",
            "Operational rules for the next attempt:",
            "- Work only inside the provided benchmark repository.",
            "- Do not copy the repository to /tmp, /home/user, or another checkout.",
            "- The only allowed /tmp path is /tmp/final.patch.",
            "- Do not create standalone Django projects, settings.py, manage.py, test_app/, or test_*.py reproduction artifacts.",
            "- If a temporary reproduction file is created, remove it before the final diff.",
            "- Apply the fix to the real source file, not to .fixed, .orig, .backup, or scratch copies.",
            "- Prefer a one-file or small source-only patch when possible.",
            "- Before final submission, inspect `git diff --stat` and remove tests, temporary files, backups, and benchmark artifacts.",
            "- Final output must be a valid unified diff generated by `git diff --binary` and checked with `git apply --check /tmp/final.patch`.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reusable evolution memory from prior feedback reports.")
    parser.add_argument("--feedback-dir", default="outputs/feedback", help="Directory containing */feedback_report.json files")
    parser.add_argument("--output", required=True, help="Output memory markdown/text file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    feedback_dir = Path(args.feedback_dir)
    reports = load_reports(feedback_dir)
    if not reports:
        raise SystemExit(f"No feedback reports found under {feedback_dir}")
    memory = build_memory(reports)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(memory, encoding="utf-8")
    print(f"reports: {len(reports)}")
    print(f"wrote: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
