#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import yaml

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
        "  /usr/bin/python3.12 scripts/prepare_swebench_local_tasks.py --split test --start 0 --limit 5 --clone\n"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def parse_list_field(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


def changed_files_from_patch(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            files.append(line.removeprefix("+++ b/"))
    return sorted(set(files))


def django_test_label(value: str) -> str | None:
    value = value.strip()
    match = re.match(r"^([A-Za-z_][\w]*)\s+\(([\w.]+)\)$", value)
    if match:
        return f"{match.group(2)}.{match.group(1)}"
    if re.match(r"^[\w.]+$", value):
        return value
    return None


def test_command(repo: str, test_names: list[str], fallback: str = "python -m pytest -q") -> str:
    if not test_names:
        return fallback
    if repo == "django/django":
        labels = [label for name in test_names if (label := django_test_label(name))]
        if labels:
            return "/usr/bin/python3.12 tests/runtests.py --verbosity 1 --parallel 1 " + " ".join(labels)
        return "/usr/bin/python3.12 tests/runtests.py --verbosity 1 --parallel 1"
    return "python -m pytest -q " + " ".join(json.dumps(name) for name in test_names)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert SWE-bench Lite records into local no-Docker task skeletons.")
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite")
    parser.add_argument("--split", default="test")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "examples" / "local_tasks" / "swebench_lite"))
    parser.add_argument("--manifest", default=str(PROJECT_ROOT / "configs" / "local_eval_swebench_lite.yaml"))
    parser.add_argument("--attempts-dir", default="outputs/local_runs/baseline")
    parser.add_argument("--clone", action="store_true", help="Clone GitHub repos and checkout base commits.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(args.dataset, split=args.split)

    tasks = []
    for index in range(args.start, min(args.start + args.limit, len(ds))):
        item = ds[index]
        instance_id = str(item["instance_id"])
        task_dir = output_root / instance_id
        repo_dir = task_dir / "repo"
        task_dir.mkdir(parents=True, exist_ok=True)

        (task_dir / "issue.md").write_text(str(item.get("problem_statement", "")), encoding="utf-8")
        (task_dir / "hidden_test.patch").write_text(str(item.get("test_patch", "")), encoding="utf-8")
        (task_dir / "reference.patch").write_text(str(item.get("patch", "")), encoding="utf-8")
        (task_dir / "record.json").write_text(json.dumps(dict(item), ensure_ascii=False, indent=2), encoding="utf-8")

        if args.clone:
            if repo_dir.exists() and args.overwrite:
                import shutil

                shutil.rmtree(repo_dir)
            if not repo_dir.exists():
                run(["git", "clone", "--no-tags", "--filter=blob:none", f"https://github.com/{item['repo']}.git", str(repo_dir)])
            run(["git", "checkout", str(item["base_commit"])], cwd=repo_dir)

        fail_to_pass = parse_list_field(item.get("FAIL_TO_PASS"))
        pass_to_pass = parse_list_field(item.get("PASS_TO_PASS"))
        hidden_command = test_command(str(item.get("repo", "")), fail_to_pass + pass_to_pass)
        fix_command = test_command(str(item.get("repo", "")), fail_to_pass) if fail_to_pass else ""
        regression_command = test_command(str(item.get("repo", "")), pass_to_pass) if pass_to_pass else ""
        relevant_files = changed_files_from_patch(str(item.get("patch", "")))

        tasks.append(
            {
                "id": instance_id,
                "base_commit": str(item.get("base_commit", "")),
                "repo_path": str(repo_dir),
                "issue": str(task_dir / "issue.md"),
                "relevant_files": relevant_files,
                "visible_test_command": "",
                "hidden_test_patch": str(task_dir / "hidden_test.patch"),
                "hidden_test_command": hidden_command,
                "fix_test_command": fix_command,
                "regression_test_command": regression_command,
                "timeout_sec": 300,
            }
        )

    manifest = {
        "systems": [
            {
                "name": "baseline",
                "attempts_dir": args.attempts_dir,
                "description": "SWE-bench Lite records converted to local tasks; not official SWE-bench scoring.",
            }
        ],
        "tasks": tasks,
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[prepare-swebench-local] wrote manifest: {manifest_path}")
    print(f"[prepare-swebench-local] wrote task skeletons under: {output_root}")
    if not args.clone:
        print("[prepare-swebench-local] repos were not cloned. Re-run with --clone on a machine with GitHub access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
