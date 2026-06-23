#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


FEATURE_NAMES = [
    "bias",
    "patch_apply",
    "visible_pass",
    "submission_compliant",
    "selection_compliant",
    "non_empty",
    "small_patch",
    "one_file",
    "test_aware",
    "semantic",
    "pairwise",
    "unsafe_penalty",
    "drift_penalty",
    "test_edit_penalty",
]


def main() -> int:
    args = parse_args()
    manifest = yaml.safe_load(resolve_path(args.manifest).read_text(encoding="utf-8"))
    tasks = manifest["tasks"][args.start : args.start + args.limit if args.limit else None]
    tasks_by_id = {str(task["id"]): task for task in tasks}
    feedback_root = resolve_path(args.feedback_root)
    eval_rows = load_candidate_metrics(resolve_path(args.candidate_metrics))
    semantic = load_semantic_scores(resolve_path(args.semantic_scores)) if args.semantic_scores else {}
    pairwise = load_pairwise_scores(resolve_path(args.pairwise_scores)) if args.pairwise_scores else {}
    selected_anchor = load_selected_anchor(resolve_path(args.selected_root)) if args.selected_root else {}
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates_by_task = load_candidates(tasks_by_id, feedback_root, eval_rows, semantic, pairwise)
    strategies = args.strategies.split(",")
    summaries = []
    for strategy in strategies:
        strategy = strategy.strip()
        if not strategy:
            continue
        selected = []
        details = []
        weights_by_task = {}
        if strategy == "calibrated":
            weights_by_task = train_leave_task_out(candidates_by_task)
        for task_id, candidates in candidates_by_task.items():
            if not candidates:
                continue
            if strategy == "anchor":
                candidate_index = selected_anchor.get(task_id)
                best = next((row for row in candidates if int(row["candidate_index"]) == candidate_index), None)
                best = best or select_original(candidates)
            elif strategy == "original":
                best = select_original(candidates)
            elif strategy == "test_aware":
                best = max(candidates, key=lambda row: (test_aware_score(row), original_score(row)))
            elif strategy == "semantic":
                best = max(candidates, key=lambda row: (semantic_selector_score(row), original_score(row)))
            elif strategy == "pairwise":
                best = max(candidates, key=lambda row: (float(row.get("pairwise_score", 0.0)), original_score(row)))
            elif strategy == "blended":
                best = max(candidates, key=lambda row: (blended_score(row), original_score(row)))
            elif strategy == "calibrated":
                weights = weights_by_task.get(task_id) or zero_weights()
                best = max(candidates, key=lambda row: (predict_probability(weights, feature_vector(row)), original_score(row)))
            else:
                raise SystemExit(f"Unknown strategy: {strategy}")
            selected.append(best)
            details.append(detail_row(strategy, best))
        summaries.append(summary_row(strategy, selected))
        write_csv(output_dir / f"selected_{strategy}.csv", details)

    summary_path = output_dir / "selector_summary.csv"
    write_csv(summary_path, summaries)
    print(f"wrote: {summary_path}")
    for row in summaries:
        print(row)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline candidate selector analysis over an existing candidate pool.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--feedback-root", required=True)
    parser.add_argument("--candidate-metrics", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--selected-root", default="", help="Optional selected-system root for anchor/original comparison.")
    parser.add_argument("--semantic-scores", default="", help="Optional JSONL produced by semantic LLM judge.")
    parser.add_argument("--pairwise-scores", default="", help="Optional JSONL produced by pairwise LLM judge.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--strategies",
        default="anchor,original,test_aware,semantic,pairwise,blended,calibrated",
        help="Comma-separated strategies to evaluate.",
    )
    return parser.parse_args()


def load_candidates(
    tasks_by_id: dict[str, dict[str, Any]],
    feedback_root: Path,
    eval_rows: dict[tuple[str, int], dict[str, str]],
    semantic: dict[tuple[str, int], dict[str, float]],
    pairwise: dict[tuple[str, int], float],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for task_id in tasks_by_id:
        report_path = feedback_root / task_id / "feedback_report.json"
        if not report_path.exists():
            out[task_id] = []
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = []
        for candidate in report.get("candidates", []):
            row = dict(candidate)
            candidate_index = int(row["candidate_index"])
            eval_row = eval_rows.get((task_id, candidate_index), {})
            row["task_id"] = task_id
            row["issue"] = str(tasks_by_id[task_id].get("issue", ""))
            row["eval"] = eval_row
            row["semantic_scores"] = semantic.get((task_id, candidate_index), {})
            row["pairwise_score"] = pairwise.get((task_id, candidate_index), 0.0)
            rows.append(row)
        out[task_id] = rows
    return out


def select_original(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = [
        [row for row in candidates if row.get("patch_apply") and row.get("selection_compliant") and row.get("visible_pass") is True],
        [row for row in candidates if row.get("patch_apply") and row.get("selection_compliant")],
        [row for row in candidates if row.get("patch_apply") and row.get("submission_compliant") and not row.get("workdir_drift")],
        [row for row in candidates if row.get("patch_apply") and row.get("submission_compliant")],
        candidates,
    ]
    for tier in tiers:
        if tier:
            return max(tier, key=original_score)
    raise ValueError("No candidates")


def original_score(row: dict[str, Any]) -> float:
    return float(row.get("score") or 0.0)


def test_aware_score(row: dict[str, Any]) -> float:
    score = 0.0
    score += 3.0 if row.get("visible_pass") is True else 0.0
    score += 2.0 if row.get("patch_apply") else -2.0
    score += 1.0 if row.get("selection_compliant") else -1.0
    score += 0.8 if row.get("submission_compliant") else -0.8
    score += 0.5 if int(row.get("patch_files") or 99) <= 2 else -0.5
    score += 0.5 if int(row.get("patch_lines") or 9999) <= 180 else -0.5
    score -= 2.0 if row.get("test_file_edit") else 0.0
    score -= 2.0 if row.get("workdir_drift") else 0.0
    score -= 1.5 if row.get("unsafe_edit") else 0.0
    score -= 1.0 if row.get("benchmark_artifact_exposure") else 0.0
    return round(score, 4)


def semantic_selector_score(row: dict[str, Any]) -> float:
    scores = row.get("semantic_scores") or {}
    root = float(scores.get("fixes_root_cause", 0.0))
    relevance = float(scores.get("test_relevance", 0.0))
    minimal = float(scores.get("minimal_and_targeted", 0.0))
    risk = float(scores.get("risk_of_regression", 0.0))
    return round(0.45 * root + 0.25 * relevance + 0.20 * minimal - 0.30 * risk + 0.10 * test_aware_score(row), 4)


def blended_score(row: dict[str, Any]) -> float:
    pairwise = float(row.get("pairwise_score", 0.0))
    semantic = semantic_selector_score(row)
    return round(0.45 * pairwise + 0.30 * semantic + 0.15 * test_aware_score(row) + 0.10 * bool_float(row.get("selection_compliant")), 4)


def feature_vector(row: dict[str, Any]) -> list[float]:
    patch_lines = float(row.get("patch_lines") or 9999)
    patch_files = float(row.get("patch_files") or 99)
    return [
        1.0,
        bool_float(row.get("patch_apply")),
        bool_float(row.get("visible_pass") is True),
        bool_float(row.get("submission_compliant")),
        bool_float(row.get("selection_compliant")),
        0.0 if row.get("empty_patch") else 1.0,
        1.0 if patch_lines <= 180 else 0.0,
        1.0 if patch_files <= 1 else 0.0,
        test_aware_score(row) / 10.0,
        semantic_selector_score(row) / 5.0,
        float(row.get("pairwise_score", 0.0)) / 3.0,
        -bool_float(row.get("unsafe_edit")),
        -bool_float(row.get("workdir_drift")),
        -bool_float(row.get("test_file_edit")),
    ]


def train_leave_task_out(candidates_by_task: dict[str, list[dict[str, Any]]]) -> dict[str, list[float]]:
    out = {}
    for heldout_task in candidates_by_task:
        train_rows = [
            row
            for task_id, rows in candidates_by_task.items()
            if task_id != heldout_task
            for row in rows
            if row.get("eval", {}).get("success") in {"True", "False"}
        ]
        out[heldout_task] = train_logistic(train_rows)
    return out


def train_logistic(rows: list[dict[str, Any]], *, epochs: int = 300, lr: float = 0.08, l2: float = 0.02) -> list[float]:
    weights = zero_weights()
    if not rows:
        return weights
    for _ in range(epochs):
        grad = [l2 * w for w in weights]
        for row in rows:
            x = feature_vector(row)
            y = 1.0 if row.get("eval", {}).get("success") == "True" else 0.0
            pred = predict_probability(weights, x)
            for i, value in enumerate(x):
                grad[i] += (pred - y) * value / len(rows)
        for i in range(len(weights)):
            weights[i] -= lr * grad[i]
    return weights


def zero_weights() -> list[float]:
    return [0.0 for _ in FEATURE_NAMES]


def predict_probability(weights: list[float], x: list[float]) -> float:
    z = sum(w * value for w, value in zip(weights, x))
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def load_candidate_metrics(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    rows = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[(str(row["task_id"]), int(row["candidate_index"]))] = row
    return rows


def load_selected_anchor(selected_root: Path) -> dict[str, int]:
    anchors = {}
    for metadata_path in selected_root.glob("*/candidate_0/metadata.json"):
        task_id = metadata_path.parents[1].name
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            value = metadata.get("selected_candidate")
            if value is not None:
                anchors[task_id] = int(value)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return anchors


def load_semantic_scores(path: Path) -> dict[tuple[str, int], dict[str, float]]:
    scores = {}
    for obj in read_jsonl(path):
        task_id = str(obj["task_id"])
        candidate_index = int(obj["candidate_index"])
        scores[(task_id, candidate_index)] = {
            "fixes_root_cause": float(obj.get("fixes_root_cause", 0.0)),
            "minimal_and_targeted": float(obj.get("minimal_and_targeted", 0.0)),
            "risk_of_regression": float(obj.get("risk_of_regression", 0.0)),
            "test_relevance": float(obj.get("test_relevance", 0.0)),
        }
    return scores


def load_pairwise_scores(path: Path) -> dict[tuple[str, int], float]:
    wins: dict[tuple[str, int], float] = {}
    for obj in read_jsonl(path):
        task_id = str(obj["task_id"])
        winner = str(obj.get("winner", "")).upper()
        confidence = float(obj.get("confidence", 1.0))
        if winner == "A":
            candidate = int(obj["candidate_a"])
        elif winner == "B":
            candidate = int(obj["candidate_b"])
        else:
            continue
        wins[(task_id, candidate)] = wins.get((task_id, candidate), 0.0) + confidence
    return wins


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def detail_row(strategy: str, row: dict[str, Any]) -> dict[str, Any]:
    eval_row = row.get("eval", {})
    return {
        "strategy": strategy,
        "task_id": row["task_id"],
        "selected_candidate": row["candidate_index"],
        "original_score": original_score(row),
        "test_aware_score": test_aware_score(row),
        "semantic_score": semantic_selector_score(row),
        "pairwise_score": row.get("pairwise_score", 0.0),
        "blended_score": blended_score(row),
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


def summary_row(strategy: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    eval_rows = [row.get("eval", {}) for row in selected]
    pass_count = sum(row.get("success") == "True" for row in eval_rows)
    return {
        "strategy": strategy,
        "selected": len(selected),
        "pass_count": pass_count,
        "pass_at_1": round(pass_count / len(selected), 4) if selected else "NA",
        "fix_pass_rate": bool_rate(eval_rows, "fix_pass"),
        "regression_pass_rate": bool_rate(eval_rows, "regression_pass"),
        "hidden_pass_rate": bool_rate(eval_rows, "hidden_pass"),
        "submission_compliance_rate": bool_rate(eval_rows, "submission_compliant"),
        "unsafe_edit_rate": bool_rate(eval_rows, "unsafe_edit"),
        "empty_patch_rate": bool_rate(eval_rows, "empty_patch"),
        "avg_patch_lines": avg_float(eval_rows, "patch_lines"),
        "avg_patch_files": avg_float(eval_rows, "patch_files"),
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


def bool_float(value: Any) -> float:
    return 1.0 if value is True else 0.0


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
