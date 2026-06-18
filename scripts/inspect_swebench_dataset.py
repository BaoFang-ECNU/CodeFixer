#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from datasets import load_dataset
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing Python package: datasets\n"
        "This usually means `pip` and `python` point to different environments.\n"
        "Check with:\n"
        "  which python\n"
        "  which pip\n"
        "  pip -V\n"
        "Find the matching system Python with:\n"
        "  head -1 $(which pip)\n"
        "  which python3 python3.12 /usr/bin/python3 /usr/bin/python3.12\n"
        "Then run this script with that Python, e.g.:\n"
        "  /usr/bin/python3.12 scripts/inspect_swebench_dataset.py --split test --limit 5\n"
    ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SWE-bench Lite records without running containers.")
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite")
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    ds = load_dataset(args.dataset, split=args.split)
    rows = []
    for i, item in enumerate(ds):
        if i >= args.limit:
            break
        row = {
            "index": i,
            "instance_id": item.get("instance_id"),
            "repo": item.get("repo"),
            "base_commit": item.get("base_commit"),
            "problem_statement": item.get("problem_statement"),
            "test_patch": item.get("test_patch"),
            "patch": item.get("patch"),
            "created_at": item.get("created_at"),
        }
        rows.append(row)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[inspect-swebench] wrote {path}")
    else:
        for row in rows:
            print("=" * 100)
            print(f"index: {row['index']}")
            print(f"instance_id: {row['instance_id']}")
            print(f"repo: {row['repo']}")
            print(f"base_commit: {row['base_commit']}")
            print("problem_statement:")
            print((row["problem_statement"] or "").strip()[:2000])
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
