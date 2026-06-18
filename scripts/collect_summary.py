#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codefixer_baseline.summarize import summarize_run, write_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect baseline run summaries.")
    parser.add_argument("--runs-dir", default=str(PROJECT_ROOT / "outputs" / "runs"))
    parser.add_argument("--eval-dir", default=str(PROJECT_ROOT / "outputs" / "eval"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "summary"))
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    eval_dir = Path(args.eval_dir)
    if not runs_dir.exists():
        print(f"[summary] No runs directory found: {runs_dir}")
        rows = []
    else:
        rows = [summarize_run(path, eval_dir=eval_dir) for path in sorted(runs_dir.iterdir()) if path.is_dir()]

    csv_path, md_path = write_summary(rows, Path(args.output_dir))
    print(f"[summary] Wrote {csv_path}")
    print(f"[summary] Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
