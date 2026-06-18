from evaluation.metrics import compute_metrics, training_artifact_metrics


def test_compute_metrics_empty():
    metrics = compute_metrics([])
    assert metrics["pass_at_1"] == 0.0


def test_compute_metrics_true_pass_at_k():
    results = [
        {"task_id": "a", "trial_id": 1, "success": False},
        {"task_id": "a", "trial_id": 2, "success": True},
        {"task_id": "b", "trial_id": 1, "success": False},
        {"task_id": "b", "trial_id": 2, "success": False},
    ]
    metrics = compute_metrics(results, pass_at_k=2)
    assert metrics["pass_at_1"] == 0.0
    assert metrics["pass_at_k"] == 0.5
    assert metrics["visible_test_pass_rate"] == 0.25


def test_training_artifact_metrics(tmp_path):
    (tmp_path / "sft_train.jsonl").write_text("{}\n{}\n", encoding="utf-8")
    (tmp_path / "rlvr_rollouts.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "guidance_train.jsonl").write_text("{}\n{}\n", encoding="utf-8")
    (tmp_path / "memory_patterns.json").write_text('{"off_by_one": 1.0}', encoding="utf-8")

    metrics = training_artifact_metrics(str(tmp_path), total_steps=4)

    assert metrics["sft_record_count"] == 2.0
    assert metrics["rlvr_rollout_count"] == 1.0
    assert metrics["guidance_coverage"] == 0.5
    assert metrics["memory_pattern_count"] == 1.0


def test_java_and_defects4j_metrics():
    metrics = compute_metrics(
        [
            {
                "task_id": "defects4j_Lang_1",
                "success": False,
                "language": "java",
                "project_source": "defects4j",
                "final_test_output": "Compilation failed: javac error",
            },
            {
                "task_id": "defects4j_Lang_2",
                "success": True,
                "language": "java",
                "project_source": "defects4j",
                "final_test_output": "all tests pass",
            },
        ]
    )
    assert metrics["java_compile_failure_rate"] == 0.5
    assert metrics["defects4j_triggering_test_pass_rate"] == 0.5
