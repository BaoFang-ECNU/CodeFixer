import subprocess
import sys
import json
from pathlib import Path


def test_benchmark_builder_smoke(tmp_path):
    root = Path.cwd()
    config_path = tmp_path / "benchmark_sources_test.yaml"
    output_tasks_file = tmp_path / "tasks_benchmark_test.yaml"
    output_dir = tmp_path / "benchmark_tasks"
    config_path.write_text(
        json.dumps({"output_tasks_file": str(output_tasks_file), "output_dir": str(output_dir)}, ensure_ascii=False),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "scripts/build_benchmark.py", "--config", str(config_path), "--max-tasks", "10"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert output_tasks_file.exists()
