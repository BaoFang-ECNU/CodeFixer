from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

NA = "NA"

SUMMARY_FIELDS = [
    "run_name",
    "subset",
    "split",
    "slice",
    "model",
    "agent",
    "temperature",
    "step_limit",
    "num_instances",
    "num_resolved",
    "resolved_rate",
    "avg_steps",
    "avg_cost",
    "avg_wall_time",
    "num_failed_runtime",
    "num_failed_eval",
    "notes",
]


def safe_get(mapping: dict[str, Any], *keys: str, default: Any = NA) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    if current is None or current == "":
        return default
    return current


def normalize_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field, NA) if row.get(field, NA) not in (None, "") else NA for field in SUMMARY_FIELDS}


def read_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        if path.suffix == ".jsonl":
            rows = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        value = json.loads(line)
                        if isinstance(value, dict):
                            rows.append(value)
            return rows
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for key in ("results", "resolved", "instances", "predictions"):
                if isinstance(value.get(key), list):
                    return [item for item in value[key] if isinstance(item, dict)]
            return [value]
    except (OSError, json.JSONDecodeError):
        return []
    return []


def _mean(values: Iterable[Any]) -> str | float:
    nums: list[float] = []
    for value in values:
        try:
            nums.append(float(value))
        except (TypeError, ValueError):
            continue
    if not nums:
        return NA
    return round(sum(nums) / len(nums), 4)


def summarize_run(run_dir: Path, eval_dir: Path | None = None) -> dict[str, Any]:
    preds = read_json_or_jsonl(run_dir / "preds.json") or read_json_or_jsonl(run_dir / "preds.jsonl")
    trajectories = list(run_dir.rglob("*traj*.json")) + list(run_dir.rglob("*trajectory*.jsonl"))
    logs = list(run_dir.rglob("*.log")) + list(run_dir.rglob("*.txt"))

    failed_runtime = 0
    for log_path in logs:
        try:
            text = log_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "traceback" in text or "error" in text:
            failed_runtime += 1

    eval_rows: list[dict[str, Any]] = []
    if eval_dir and eval_dir.exists():
        for path in eval_dir.rglob("*.json"):
            eval_rows.extend(read_json_or_jsonl(path))

    resolved = 0
    failed_eval = 0
    for row in eval_rows:
        status = str(row.get("resolved", row.get("status", ""))).lower()
        if status in {"true", "resolved", "pass", "passed"}:
            resolved += 1
        elif status:
            failed_eval += 1

    num_instances = len(preds) if preds else len(trajectories) or NA
    rate: str | float = NA
    if isinstance(num_instances, int) and num_instances > 0 and eval_rows:
        rate = round(resolved / num_instances, 4)

    return normalize_summary_row(
        {
            "run_name": run_dir.name,
            "subset": "Lite",
            "split": "test",
            "slice": _slice_from_name(run_dir.name),
            "model": "hosted_vllm/qwen3-coder-30b-a3b",
            "agent": "vanilla mini-SWE-agent",
            "temperature": 0,
            "step_limit": 80,
            "num_instances": num_instances,
            "num_resolved": resolved if eval_rows else NA,
            "resolved_rate": rate,
            "avg_steps": _mean(safe_get(row, "steps") for row in preds),
            "avg_cost": _mean(safe_get(row, "cost") for row in preds),
            "avg_wall_time": _mean(safe_get(row, "wall_time") for row in preds),
            "num_failed_runtime": failed_runtime,
            "num_failed_eval": failed_eval if eval_rows else NA,
            "notes": "auto-collected; missing fields are NA",
        }
    )


def _slice_from_name(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit():
        return f"{parts[-2]}:{parts[-1]}"
    if parts and parts[-1].isdigit():
        return parts[-1]
    return NA


def write_summary(rows: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "baseline_summary.csv"
    md_path = output_dir / "baseline_summary.md"

    normalized = [normalize_summary_row(row) for row in rows]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)

    lines = ["| " + " | ".join(SUMMARY_FIELDS) + " |", "| " + " | ".join(["---"] * len(SUMMARY_FIELDS)) + " |"]
    for row in normalized:
        lines.append("| " + " | ".join(str(row[field]) for field in SUMMARY_FIELDS) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path
