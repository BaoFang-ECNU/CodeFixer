from pathlib import Path

from env.task_loader import load_tasks


def test_load_toy_tasks():
    tasks = load_tasks(Path("configs/tasks_toy.yaml"))
    assert len(tasks) >= 8
    assert tasks[0].task_id == "task_001"

