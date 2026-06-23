#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_SPEC = importlib.util.spec_from_file_location("safe_final_rerank", PROJECT_ROOT / "scripts" / "safe_final_rerank.py")
assert SAFE_SPEC is not None
safe_final_rerank = importlib.util.module_from_spec(SAFE_SPEC)
assert SAFE_SPEC.loader is not None
SAFE_SPEC.loader.exec_module(safe_final_rerank)


def main() -> int:
    args = parse_args()
    feedback_root = resolve_path(args.feedback_root)
    memory_counts = safe_final_rerank.load_memory_counts(resolve_path(args.memory_file))
    eval_rows = load_candidate_metrics(resolve_path(args.candidate_metrics))
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    for scale in parse_float_list(args.scales):
        selected = []
        missing = []
        details = []
        for report_path in sorted(feedback_root.glob("*/feedback_report.json")):
            report = json.loads(report_path.read_text(encoding="utf-8"))
            task_id = str(report["task_id"])
            candidates = [dict(row) for row in report.get("candidates", [])]
            if not candidates:
                missing.append((task_id, "no_candidates"))
                continue
            best = safe_final_rerank.select_memory_safe_candidate(
                candidates,
                memory_counts,
                penalty_scale=scale,
                hard_filter=not args.no_hard_filter,
            )
            candidate_index = int(best["candidate_index"])
            eval_row = eval_rows.get((task_id, candidate_index))
            if eval_row is None:
                missing.append((task_id, candidate_index))
                continue
            selected.append(eval_row)
            details.append(detail_row(task_id, scale, best, eval_row))

        row = summarize_selection(scale, selected, missing)
        summary.append(row)
        write_csv(output_dir / f"safe_final_selected_scale_{scale}.csv", details)

    summary_path = output_dir / "safe_final_penalty_curve.csv"
    write_csv(summary_path, summary)
    print(f"wrote: {summary_path}")
    for row in summary:
        print(row)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze safe-final penalty-scale curves without copying selected patches.")
    parser.add_argument("--feedback-root", required=True, help="Feedback reports for the generated candidate pool.")
    parser.add_argument("--candidate-metrics", required=True, help="candidate_metrics.csv from full candidate-pool eval.")
    parser.add_argument("--memory-file", required=True, help="Evolution memory markdown with failure-mode counts.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--scales", default="0,0.25,0.5,1,2,3,4,6,8")
    parser.add_argument("--no-hard-filter", action="store_true")
    return parser.parse_args()


def load_candidate_metrics(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    rows: dict[tuple[str, int], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[(str(row["task_id"]), int(row["candidate_index"]))] = row
    return rows


def detail_row(task_id: str, scale: float, best: dict[str, Any], eval_row: dict[str, str]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "penalty_scale": scale,
        "selected_candidate": best["candidate_index"],
        "safe_final_score": best["safe_final_score"],
        "memory_penalty_total": round(sum(best.get("memory_penalties", {}).values()), 4),
        "hard_rule_violations": json.dumps(best.get("hard_rule_violations", []), ensure_ascii=False),
        "success": eval_row.get("success", ""),
        "fix_pass": eval_row.get("fix_pass", ""),
        "regression_pass": eval_row.get("regression_pass", ""),
        "hidden_pass": eval_row.get("hidden_pass", ""),
        "submission_compliant": eval_row.get("submission_compliant", ""),
        "unsafe_edit": eval_row.get("unsafe_edit", ""),
        "empty_patch": eval_row.get("empty_patch", ""),
        "patch_lines": eval_row.get("patch_lines", ""),
        "patch_files": eval_row.get("patch_files", ""),
    }


def summarize_selection(scale: float, selected: list[dict[str, str]], missing: list[Any]) -> dict[str, Any]:
    pass_count = sum(row.get("success") == "True" for row in selected)
    return {
        "penalty_scale": scale,
        "selected": len(selected),
        "missing": len(missing),
        "pass_count": pass_count,
        "pass_at_1": round(pass_count / len(selected), 4) if selected else "NA",
        "fix_pass_rate": bool_rate(selected, "fix_pass"),
        "regression_pass_rate": bool_rate(selected, "regression_pass"),
        "hidden_pass_rate": bool_rate(selected, "hidden_pass"),
        "submission_compliance_rate": bool_rate(selected, "submission_compliant"),
        "unsafe_edit_rate": bool_rate(selected, "unsafe_edit"),
        "empty_patch_rate": bool_rate(selected, "empty_patch"),
        "avg_patch_lines": avg_float(selected, "patch_lines"),
        "avg_patch_files": avg_float(selected, "patch_files"),
    }


def bool_rate(rows: list[dict[str, str]], field: str) -> float | str:
    values = [row[field] for row in rows if row.get(field) in {"True", "False"}]
    if not values:
        return "NA"
    return round(sum(value == "True" for value in values) / len(values), 4)


def avg_float(rows: list[dict[str, str]], field: str) -> float | str:
    values = []
    for row in rows:
        try:
            values.append(float(row[field]))
        except (KeyError, TypeError, ValueError):
            continue
    if not values:
        return "NA"
    return round(sum(values) / len(values), 4)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
