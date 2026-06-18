from training.self_evolution import SelfEvolutionTrainer


def test_self_evolution_exports_bug_success_rates(tmp_path):
    trajectories = [
        {
            "task_id": "t",
            "success": True,
            "steps": [
                {
                    "observation": {"bug_type_hint": "off_by_one"},
                    "action": "edit_file",
                    "action_args": {"rationale": "fix off by one"},
                    "reward": 1.0,
                }
            ],
        }
    ]
    evolved = SelfEvolutionTrainer().evolve(trajectories, output_dir=tmp_path, logs_dir=tmp_path)
    assert evolved["bug_type_success_rate"]["off_by_one"] == 1.0
    assert (tmp_path / "memory_patterns.json").exists()
    assert (tmp_path / "rwr_train.jsonl").exists()
    assert (tmp_path / "sft_train.jsonl").exists()
    assert (tmp_path / "rlvr_rollouts.jsonl").exists()
    assert (tmp_path / "guidance_train.jsonl").exists()
    assert (tmp_path / "evolution_report.md").exists()


def test_self_evolution_exports_failure_only_rlvr_records(tmp_path):
    trajectories = [
        {
            "task_id": "failing_task",
            "success": False,
            "total_reward": -0.2,
            "steps": [
                {
                    "task_id": "failing_task",
                    "observation": {"issue": "fix empty input", "bug_type_hint": "empty_boundary"},
                    "action": "run_tests",
                    "action_args": {"command": "python -m pytest"},
                    "test_output": "FAILED AssertionError",
                    "reward": -0.2,
                    "done": False,
                    "patch_diff": "",
                }
            ],
        }
    ]
    evolved = SelfEvolutionTrainer().evolve(trajectories, output_dir=tmp_path, logs_dir=tmp_path)
    assert evolved["num_success"] == 0
    rlvr_text = (tmp_path / "rlvr_rollouts.jsonl").read_text(encoding="utf-8")
    guidance_text = (tmp_path / "guidance_train.jsonl").read_text(encoding="utf-8")
    assert "failing_task" in rlvr_text
    assert "prompt" in rlvr_text
    assert "repair_hint" in guidance_text
