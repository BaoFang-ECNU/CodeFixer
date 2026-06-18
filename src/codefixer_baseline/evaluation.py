from __future__ import annotations

from pathlib import Path


def choose_predictions_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.exists():
        return candidate
    if candidate.suffix == ".json":
        jsonl = candidate.with_suffix(".jsonl")
        if jsonl.exists():
            return jsonl
    if candidate.suffix == ".jsonl":
        json_path = candidate.with_suffix(".json")
        if json_path.exists():
            return json_path
    raise FileNotFoundError(f"No predictions file found at {candidate} or matching .json/.jsonl variant")
