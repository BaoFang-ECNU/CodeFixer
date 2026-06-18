#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_DROP_NAMES = {
    "__init__.py",
    "manage.py",
    "settings.py",
    "simple_test.py",
    "quick_test.py",
    "verification.py",
}


DEFAULT_DROP_SUFFIXES = (
    ".backup",
    ".bak",
    ".orig",
    ".original",
    ".fixed",
    ".patch",
)


DEFAULT_DROP_PREFIXES = (
    "temp_",
    "test_",
    "debug_",
    "reproduce_",
)


def changed_file_from_diff_header(line: str) -> str | None:
    parts = line.split()
    if len(parts) < 4 or not parts[0:2] == ["diff", "--git"]:
        return None
    right = parts[3]
    return right[2:] if right.startswith("b/") else right


def should_keep(path: str, allow_prefix: str) -> bool:
    posix = Path(path).as_posix()
    parts = posix.split("/")
    name = parts[-1] if parts else posix

    if not posix.startswith(allow_prefix.rstrip("/") + "/"):
        return False
    if "tests" in parts:
        return False
    if name in DEFAULT_DROP_NAMES:
        return False
    if name.endswith(DEFAULT_DROP_SUFFIXES):
        return False
    if name.startswith(DEFAULT_DROP_PREFIXES):
        return False
    if name.endswith("_test.py"):
        return False
    return True


def split_diff_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            chunks.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("".join(current))
    return chunks


def clean_patch(path: Path, allow_prefix: str, backup_suffix: str, dry_run: bool) -> tuple[int, int]:
    original = path.read_text(encoding="utf-8", errors="ignore")
    kept: list[str] = []
    dropped = 0
    for chunk in split_diff_chunks(original):
        first = chunk.splitlines()[0] if chunk.splitlines() else ""
        changed = changed_file_from_diff_header(first)
        if changed and should_keep(changed, allow_prefix):
            kept.append(chunk)
        elif changed:
            dropped += 1

    if not dry_run:
        backup = path.with_name(path.name + backup_suffix)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text("".join(kept), encoding="utf-8")
    return len(kept), dropped


def iter_patch_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.glob("*/candidate_*/patch.diff"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove temporary/test/non-source diffs from local candidate patches.")
    parser.add_argument("--runs-dir", default="outputs/local_runs/baseline")
    parser.add_argument("--allow-prefix", default="django")
    parser.add_argument("--backup-suffix", default=".raw")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.runs_dir)
    patches = iter_patch_files(root)
    print(f"[clean-patches] patch files: {len(patches)}")
    total_kept = 0
    total_dropped = 0
    for patch in patches:
        kept, dropped = clean_patch(patch, args.allow_prefix, args.backup_suffix, args.dry_run)
        total_kept += kept
        total_dropped += dropped
        if dropped:
            print(f"[clean-patches] {patch}: kept={kept} dropped={dropped}")

    action = "would update" if args.dry_run else "updated"
    print(f"[clean-patches] {action}: kept_diffs={total_kept} dropped_diffs={total_dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
