#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codefixer_baseline.local_eval import evaluate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate local code-repair tasks without Docker/SWE-bench containers.")
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_example.yaml"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "local_eval"))
    args = parser.parse_args()

    candidates, systems = evaluate_manifest(args.manifest, args.output_dir)
    print(f"[local-eval] evaluated candidates: {len(candidates)}")
    print(f"[local-eval] evaluated systems: {len(systems)}")
    print(f"[local-eval] wrote outputs under: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
