from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SweepRunSpec:
    start: int
    end: int
    output_dir: Path
    split: str = "test"
    subset: str = "lite"
    workers: int = 1

    @property
    def run_name(self) -> str:
        return self.output_dir.name


def validate_slice(start: int, end: int) -> None:
    if start < 0:
        raise ValueError("start must be >= 0")
    if end <= start:
        raise ValueError("end must be greater than start")
