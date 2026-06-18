#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path


def contains_error(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "traceback" in text or "error" in text or "exception" in text


def read_status(path: Path) -> str:
    try:
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        row = json.loads(line)
                        if isinstance(row, dict):
                            return str(row.get("status") or row.get("resolved") or row.get("instance_id") or "NA")
        else:
            row = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(row, dict):
                return str(row.get("status") or row.get("resolved") or row.get("instance_id") or "NA")
            if isinstance(row, list) and row and isinstance(row[0], dict):
                return str(row[0].get("status") or row[0].get("resolved") or row[0].get("instance_id") or "NA")
    except (OSError, json.JSONDecodeError):
        return "NA"
    return "NA"


def inspect_run(run_dir: Path) -> dict[str, str]:
    json_files = list(run_dir.rglob("*.json")) + list(run_dir.rglob("*.jsonl"))
    logs = list(run_dir.rglob("*.log")) + list(run_dir.rglob("*.txt"))
    preds = [p for p in json_files if p.name in {"preds.json", "preds.jsonl"}]
    trajectories = [p for p in json_files if "traj" in p.name.lower() or "trajectory" in p.name.lower()]
    errored = any(contains_error(path) for path in logs)
    status = read_status(preds[0]) if preds else (read_status(trajectories[0]) if trajectories else "NA")
    return {
        "run": run_dir.name,
        "preds": str(preds[0]) if preds else "NA",
        "trajectories": str(len(trajectories)),
        "logs": str(len(logs)),
        "has_error": str(errored),
        "status": status,
    }


def print_table(rows: list[dict[str, str]]) -> None:
    headers = ["run", "preds", "trajectories", "logs", "has_error", "status"]
    widths = {h: max(len(h), *(len(row[h]) for row in rows)) if rows else len(h) for h in headers}
    print("  ".join(h.ljust(widths[h]) for h in headers))
    print("  ".join("-" * widths[h] for h in headers))
    for row in rows:
        print("  ".join(row[h].ljust(widths[h]) for h in headers))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect CodeFixer baseline run outputs.")
    parser.add_argument("runs_dir", nargs="?", default="outputs/runs", help="Directory containing run subdirectories.")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        print(f"No runs directory found: {runs_dir}")
        return 0
    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    rows = [inspect_run(path) for path in sorted(run_dirs)]
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
