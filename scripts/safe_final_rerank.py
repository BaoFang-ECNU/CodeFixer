#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


DEFAULT_SEVERE_RULES = {
    "benchmark_artifact_content_access",
    "test_file_edit",
    "artifact_file_edit",
}


def main() -> int:
    args = parse_args()
    task_ids = load_task_ids(resolve_path(args.manifest), args.start, args.limit)
    memory_counts = load_memory_counts(resolve_path(args.memory_file))
    feedback_root = resolve_path(args.feedback_root)
    selected_root = PROJECT_ROOT / "outputs" / "local_runs" / args.selected_system
    report_root = resolve_path(args.output_report_root)
    report_root.mkdir(parents=True, exist_ok=True)

    selected = 0
    missing_reports: list[str] = []
    for task_id in task_ids:
        feedback_report = feedback_root / task_id / "feedback_report.json"
        if not feedback_report.exists():
            missing_reports.append(task_id)
            continue
        data = json.loads(feedback_report.read_text(encoding="utf-8"))
        candidates = [dict(row) for row in data.get("candidates", [])]
        if not candidates:
            missing_reports.append(task_id)
            continue
        best = select_memory_safe_candidate(
            candidates,
            memory_counts,
            penalty_scale=args.penalty_scale,
            hard_filter=not args.no_hard_filter,
        )
        selected_dir = selected_root / task_id / "candidate_0"
        copy_candidate(best["candidate_dir"], selected_dir)
        write_metadata(selected_dir, args, best, memory_counts, candidates)
        write_report(report_root / task_id / "safe_final_report.json", args, task_id, best, candidates, memory_counts)
        selected += 1
        print(f"[safe-final] {task_id} selected candidate_{best['candidate_index']} score={best['safe_final_score']}")

    print(f"[safe-final] selected tasks: {selected}")
    print(f"[safe-final] missing reports: {len(missing_reports)}")
    for task_id in missing_reports[:50]:
        print(f"[safe-final] missing report: {task_id}")
    return 0 if not missing_reports else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline memory-derived safe-final reranker.")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--candidate-system", required=True, help="Existing generated candidate system name.")
    parser.add_argument("--selected-system", required=True, help="Output selected system name.")
    parser.add_argument("--feedback-root", required=True, help="Feedback reports for the candidate system.")
    parser.add_argument("--memory-file", required=True, help="Evolution memory markdown with failure-mode counts.")
    parser.add_argument("--output-report-root", required=True, help="Directory for safe-final reranker reports.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--penalty-scale", type=float, default=6.0)
    parser.add_argument("--no-hard-filter", action="store_true", help="Disable severe safety hard filters.")
    return parser.parse_args()


def load_task_ids(manifest: Path, start: int, limit: int) -> list[str]:
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    tasks = [str(task["id"]) for task in data.get("tasks", [])]
    if limit:
        return tasks[start : start + limit]
    return tasks[start:]


def load_memory_counts(memory_file: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    in_failure_section = False
    for raw_line in memory_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line == "Frequent failure modes to avoid:":
            in_failure_section = True
            continue
        if in_failure_section and not line:
            break
        if not in_failure_section or not line.startswith("- "):
            continue
        item = line[2:]
        if ":" not in item:
            continue
        name, value = item.rsplit(":", 1)
        try:
            counts[name.strip()] = int(value.strip())
        except ValueError:
            continue
    return counts


def select_memory_safe_candidate(
    candidates: list[dict[str, Any]],
    memory_counts: dict[str, int],
    *,
    penalty_scale: float = 6.0,
    hard_filter: bool = True,
) -> dict[str, Any]:
    scored = []
    for row in candidates:
        scored_row = dict(row)
        scored_row["memory_penalties"] = memory_penalties(scored_row, memory_counts, penalty_scale)
        scored_row["hard_rule_violations"] = hard_rule_violations(scored_row)
        scored_row["safe_final_score"] = safe_final_score(scored_row)
        scored.append(scored_row)

    feasible = [row for row in scored if not row["hard_rule_violations"]] if hard_filter else scored
    if not feasible:
        feasible = scored
    tiers = [
        [row for row in feasible if row.get("patch_apply") and row.get("visible_pass") is True and row.get("submission_compliant")],
        [row for row in feasible if row.get("patch_apply") and row.get("submission_compliant")],
        [row for row in feasible if row.get("patch_apply")],
        feasible,
    ]
    for tier in tiers:
        if tier:
            return max(tier, key=lambda row: (row["safe_final_score"], -int(row.get("patch_lines") or 0)))
    raise ValueError("No candidates to select from")


def safe_final_score(row: dict[str, Any]) -> float:
    score = 0.0
    score += 85 if row.get("patch_apply") else -90
    score += 65 if row.get("visible_pass") is True else 0
    score -= 25 if row.get("visible_pass") is False else 0
    score += 25 if row.get("submission_compliant") else -30
    score += 12 if row.get("selection_compliant") else 0
    score += 8 if not row.get("empty_patch") else -35
    score -= 30 if row.get("malformed_patch") else 0
    score -= min(12, int(row.get("patch_files") or 0) * 2)
    score -= min(18, max(0, int(row.get("patch_lines") or 0) - 220) / 20)
    score -= sum(row.get("memory_penalties", {}).values())
    return round(score, 4)


def memory_penalties(row: dict[str, Any], counts: dict[str, int], penalty_scale: float) -> dict[str, float]:
    active = active_failure_modes(row)
    penalties: dict[str, float] = {}
    for name in active:
        count = counts.get(name, 0)
        if count <= 0:
            continue
        penalties[name] = round(penalty_scale * math.log1p(count), 4)
    return penalties


def active_failure_modes(row: dict[str, Any]) -> list[str]:
    modes: list[str] = []
    for name in [
        "empty_patch",
        "malformed_patch",
        "test_file_edit",
        "artifact_file_edit",
        "unsafe_edit",
        "workdir_drift",
        "benchmark_artifact_exposure",
        "benchmark_artifact_content_access",
    ]:
        if row.get(name):
            modes.append(name)
    if not row.get("patch_apply"):
        modes.append("patch_apply_failed")
    if row.get("visible_pass") is False:
        modes.append("visible_failed")
    if int(row.get("patch_lines") or 0) > 300:
        modes.append("large_patch")
    if int(row.get("patch_files") or 0) > 5:
        modes.append("many_files")
    return modes


def hard_rule_violations(row: dict[str, Any]) -> list[str]:
    violations = [name for name in DEFAULT_SEVERE_RULES if row.get(name)]
    changed_files = [str(path) for path in row.get("changed_files", [])]
    for path in changed_files:
        lower = Path(path).as_posix().lower()
        name = Path(lower).name
        if name in {"manage.py", "settings.py", "test_settings.py"}:
            violations.append(f"forbidden_file:{path}")
        if "test_app/" in lower or "test_reproduction/" in lower:
            violations.append(f"reproduction_artifact:{path}")
        if name.endswith((".fixed", ".backup", ".orig", ".bak")):
            violations.append(f"backup_artifact:{path}")
    return sorted(set(violations))


def copy_candidate(src: str, dst: Path) -> None:
    src_path = Path(src)
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_path, dst)


def write_metadata(
    selected_dir: Path,
    args: argparse.Namespace,
    best: dict[str, Any],
    memory_counts: dict[str, int],
    candidates: list[dict[str, Any]],
) -> None:
    metadata_path = selected_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    metadata.update(
        {
            "system": args.selected_system,
            "safe_final_candidate_system": args.candidate_system,
            "safe_final_feedback_root": args.feedback_root,
            "safe_final_memory_file": args.memory_file,
            "safe_final_selected_candidate": best["candidate_index"],
            "safe_final_score": best["safe_final_score"],
            "safe_final_memory_penalties": best.get("memory_penalties", {}),
            "safe_final_hard_rule_violations": best.get("hard_rule_violations", []),
            "safe_final_candidate_count": len(candidates),
            "safe_final_memory_failure_counts": memory_counts,
            "notes": "offline two-stage reranking: no-memory generation plus memory-derived safe_final selection",
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    args: argparse.Namespace,
    task_id: str,
    best: dict[str, Any],
    candidates: list[dict[str, Any]],
    memory_counts: dict[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "candidate_system": args.candidate_system,
                "selected_system": args.selected_system,
                "memory_file": args.memory_file,
                "penalty_scale": args.penalty_scale,
                "hard_filter": not args.no_hard_filter,
                "memory_failure_counts": memory_counts,
                "best": best,
                "candidates": candidates,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
