"""DPO preference data export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_dpo_pairs(pairs: list[dict[str, Any]], path: str | Path) -> None:
    """Write chosen/rejected preference pairs as JSONL."""

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair, ensure_ascii=False) + "\n")

