from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def outputs_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "outputs"


def runs_dir(root: Path | None = None) -> Path:
    return outputs_dir(root) / "runs"


def summary_dir(root: Path | None = None) -> Path:
    return outputs_dir(root) / "summary"


def run_dir(run_name: str, root: Path | None = None) -> Path:
    if not run_name:
        raise ValueError("run_name must be non-empty")
    return runs_dir(root) / run_name


def ensure_output_dirs(root: Path | None = None) -> None:
    outputs_dir(root).mkdir(parents=True, exist_ok=True)
    runs_dir(root).mkdir(parents=True, exist_ok=True)
    summary_dir(root).mkdir(parents=True, exist_ok=True)
