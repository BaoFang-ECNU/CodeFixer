"""On-policy distillation data export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_opd_records(records: list[dict[str, Any]], path: str | Path) -> None:
    """Write teacher-action records for distillation as JSONL."""

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

