import subprocess
import sys
from pathlib import Path


def test_benchmark_builder_smoke():
    root = Path.cwd()
    completed = subprocess.run([sys.executable, "scripts/build_benchmark.py", "--max-tasks", "10"], cwd=root, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert (root / "configs/tasks_benchmark.yaml").exists()

