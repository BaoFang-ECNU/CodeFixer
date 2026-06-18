import json

from env.defects4j_adapter import Defects4JAdapter


def test_defects4j_task_config_generation(tmp_path):
    adapter = Defects4JAdapter()
    spec = adapter.build_task_spec("Lang", 1, workspace_root=tmp_path / "workspaces")
    config_path = tmp_path / "tasks_defects4j.yaml"
    issue_dir = tmp_path / "issues"

    adapter.write_task_config([spec], config_path, issue_dir)

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    task = payload["tasks"][0]
    assert task["task_id"] == "defects4j_Lang_1"
    assert task["language"] == "java"
    assert task["project_source"] == "defects4j"
    assert task["visible_test_command"] == "defects4j test"
    assert (issue_dir / "defects4j_Lang_1.md").exists()

