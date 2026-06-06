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

