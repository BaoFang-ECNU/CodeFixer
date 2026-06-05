from pathlib import Path

from env.swebench_loader import load_swebench_lite_tasks


def test_load_swebench_lite_metadata(tmp_path):
    config = tmp_path / "tasks.json"
    config.write_text(
        '{"tasks":[{"instance_id":"demo__1","repo":"https://example.com/repo.git","base_commit":"abc","problem_statement":"fix bug","test_command":"python -m pytest"}]}',
        encoding="utf-8",
    )
    tasks = load_swebench_lite_tasks(config, issue_dir=tmp_path / "issues")
    assert tasks[0].task_id == "demo__1"
    assert tasks[0].metadata["base_commit"] == "abc"
    assert (tmp_path / "issues" / "demo__1.md").exists()

