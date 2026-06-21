#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


VALID_DIFF_HEADER = re.compile(r"^diff --git a/.+ b/.+$", re.M)


def changed_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[2].startswith("a/") and parts[3].startswith("b/"):
            files.append(parts[3][2:])
    return sorted(set(files))


def is_test_file(path: str) -> bool:
    posix = Path(path).as_posix().lower()
    parts = posix.split("/")
    name = parts[-1] if parts else posix
    return (
        "tests" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name in {"conftest.py", "pytest.ini", "tox.ini"}
    )


def classify_prediction(instance_id: str, obj: dict[str, Any]) -> dict[str, Any]:
    patch = str(obj.get("model_patch", ""))
    files = changed_files(patch)
    empty = not bool(patch.strip())
    malformed = (not empty) and not bool(VALID_DIFF_HEADER.search(patch))
    test_edit = any(is_test_file(path) for path in files)
    valid_unified_diff = (not empty) and (not malformed)
    submission_compliant = valid_unified_diff and not test_edit
    return {
        "instance_id": instance_id,
        "empty_patch": empty,
        "malformed_patch": malformed,
        "valid_unified_diff": valid_unified_diff,
        "test_file_edit": test_edit,
        "submission_compliant": submission_compliant,
        "patch_chars": len(patch),
        "patch_files": len(files),
        "changed_files": ";".join(files),
    }


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("predictions file must be a JSON object keyed by instance_id")
    return data


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "instance_id",
        "empty_patch",
        "malformed_patch",
        "valid_unified_diff",
        "test_file_edit",
        "submission_compliant",
        "patch_chars",
        "patch_files",
        "changed_files",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_strict_predictions(path: Path, predictions: dict[str, dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    by_id = {row["instance_id"]: row for row in rows}
    strict = json.loads(json.dumps(predictions))
    for instance_id, obj in strict.items():
        row = by_id[instance_id]
        if not row["submission_compliant"]:
            obj["model_patch"] = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(strict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit SWE-bench predictions for patch output protocol compliance.")
    parser.add_argument("predictions", help="Path to preds.json")
    parser.add_argument("--output-csv", default="", help="Optional CSV report path")
    parser.add_argument(
        "--write-strict-preds",
        default="",
        help="Optional output preds.json with non-compliant patches replaced by empty patches.",
    )
    parser.add_argument("--fail-on-invalid", action="store_true", help="Return nonzero if any prediction is non-compliant.")
    args = parser.parse_args()

    predictions_path = Path(args.predictions)
    predictions = load_predictions(predictions_path)
    rows = [classify_prediction(instance_id, obj) for instance_id, obj in predictions.items()]

    total = len(rows)
    empty = sum(1 for row in rows if row["empty_patch"])
    malformed = sum(1 for row in rows if row["malformed_patch"])
    valid = sum(1 for row in rows if row["valid_unified_diff"])
    test_edits = sum(1 for row in rows if row["test_file_edit"])
    compliant = sum(1 for row in rows if row["submission_compliant"])

    print(f"total: {total}")
    print(f"empty_patch: {empty}")
    print(f"malformed_patch: {malformed}")
    print(f"valid_unified_diff: {valid}")
    print(f"test_file_edit: {test_edits}")
    print(f"submission_compliant: {compliant}")

    non_compliant = [row for row in rows if not row["submission_compliant"]]
    if non_compliant:
        print("\nnon-compliant instances:")
        for row in non_compliant:
            reasons = []
            if row["empty_patch"]:
                reasons.append("empty")
            if row["malformed_patch"]:
                reasons.append("malformed")
            if row["test_file_edit"]:
                reasons.append("test_edit")
            print(f"- {row['instance_id']}: {','.join(reasons)}")

    if args.output_csv:
        write_csv(Path(args.output_csv), rows)
        print(f"\nwrote csv: {args.output_csv}")
    if args.write_strict_preds:
        write_strict_predictions(Path(args.write_strict_preds), predictions, rows)
        print(f"wrote strict predictions: {args.write_strict_preds}")

    return 1 if args.fail_on_invalid and non_compliant else 0


if __name__ == "__main__":
    raise SystemExit(main())
