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
    selected_root = resolve_path(args.selected_root) if args.selected_root else None
    memory_counts = safe_final_rerank.load_memory_counts(resolve_path(args.memory_file))
    eval_rows = load_candidate_metrics(resolve_path(args.candidate_metrics))
    tau_values = parse_float_list(args.taus)
    epsilon_values = parse_float_list(args.epsilons)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    for tau in tau_values:
        for epsilon in epsilon_values:
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
                original_candidate = load_selected_candidate_index(selected_root, task_id) if selected_root else None
                best = select_with_memory_tiebreaker(
                    candidates,
                    memory_counts,
                    tau=tau,
                    epsilon=epsilon,
                    original_candidate_index=original_candidate,
                )
                candidate_index = int(best["candidate_index"])
                eval_row = eval_rows.get((task_id, candidate_index))
                if eval_row is None:
                    missing.append((task_id, candidate_index))
                    continue
                selected.append(eval_row)
                details.append(detail_row(task_id, best, eval_row))

            row = summarize_selection(tau, epsilon, selected, missing)
            summary.append(row)
            write_csv(output_dir / f"selected_tau_{tau}_eps_{epsilon}.csv", details)

    summary_path = output_dir / "memory_tiebreaker_curve.csv"
    write_csv(summary_path, summary)
    print(f"wrote: {summary_path}")
    for row in summary:
        print(row)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze original-selector + memory tie-breaker curves offline.")
    parser.add_argument("--feedback-root", required=True, help="Feedback reports for the generated candidate pool.")
    parser.add_argument(
        "--selected-root",
        help="Selected-system directory with candidate_0/metadata.json. "
        "When set, use its selected_candidate as the exact original selector anchor.",
    )
    parser.add_argument("--candidate-metrics", required=True, help="candidate_metrics.csv from full candidate-pool eval.")
    parser.add_argument("--memory-file", required=True, help="Evolution memory markdown with failure-mode counts.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--taus", default="0,5,10,20,40", help="Comma-separated original-score tie windows.")
    parser.add_argument("--epsilons", default="0,0.05,0.1,0.2,0.5,1.0", help="Comma-separated memory penalty weights.")
    parser.add_argument("--penalty-scale", type=float, default=1.0, help="Base scale for memory risk before epsilon.")
    return parser.parse_args()


def select_with_memory_tiebreaker(
    candidates: list[dict[str, Any]],
    memory_counts: dict[str, int],
    *,
    tau: float,
    epsilon: float,
    original_candidate_index: int | None = None,
) -> dict[str, Any]:
    scored = []
    for row in candidates:
        item = dict(row)
        original_score = float(item.get("score") or 0.0)
        memory_risk = sum(safe_final_rerank.memory_penalties(item, memory_counts, 1.0).values())
        item["original_score"] = original_score
        item["memory_risk"] = round(memory_risk, 4)
        item["tiebreaker_score"] = round(original_score - epsilon * memory_risk, 4)
        scored.append(item)

    if original_candidate_index is not None:
        original = next((row for row in scored if int(row["candidate_index"]) == original_candidate_index), None)
        if original is not None:
            if epsilon == 0:
                return original
            original_score = float(original["original_score"])
            eligible = [
                row
                for row in scored
                if 0 <= original_score - float(row["original_score"]) <= tau
            ]
            if original not in eligible:
                eligible.append(original)
            return max(
                eligible,
                key=lambda row: (row["tiebreaker_score"], row["original_score"], -int(row.get("patch_lines") or 0)),
            )

    tier = original_selector_tier(scored)
    max_original = max(float(row["original_score"]) for row in tier)
    eligible = [row for row in tier if max_original - float(row["original_score"]) <= tau]
    return max(eligible, key=lambda row: (row["tiebreaker_score"], row["original_score"], -int(row.get("patch_lines") or 0)))


def original_selector_tier(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match run_feedback_task.select_best_report()'s tiering before tie-breaking."""
    tiers = [
        [row for row in candidates if row.get("patch_apply") and row.get("selection_compliant") and row.get("visible_pass") is True],
        [row for row in candidates if row.get("patch_apply") and row.get("selection_compliant")],
        [
            row
            for row in candidates
            if row.get("patch_apply") and row.get("submission_compliant") and not row.get("workdir_drift")
        ],
        [row for row in candidates if row.get("patch_apply") and row.get("submission_compliant")],
        candidates,
    ]
    for tier in tiers:
        if tier:
            return tier
    raise ValueError("No candidates to select from")


def load_candidate_metrics(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    rows: dict[tuple[str, int], dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[(str(row["task_id"]), int(row["candidate_index"]))] = row
    return rows


def load_selected_candidate_index(selected_root: Path | None, task_id: str) -> int | None:
    if selected_root is None:
        return None
    metadata_path = selected_root / task_id / "candidate_0" / "metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        value = metadata.get("selected_candidate")
        return int(value) if value is not None else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def detail_row(task_id: str, best: dict[str, Any], eval_row: dict[str, str]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "selected_candidate": best["candidate_index"],
        "original_score": best["original_score"],
        "memory_risk": best["memory_risk"],
        "tiebreaker_score": best["tiebreaker_score"],
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


def summarize_selection(tau: float, epsilon: float, selected: list[dict[str, str]], missing: list[Any]) -> dict[str, Any]:
    pass_count = sum(row.get("success") == "True" for row in selected)
    return {
        "tau": tau,
        "epsilon": epsilon,
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
