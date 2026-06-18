from env.task_loader import load_yaml
from training.resource_registry import apply_resource_selection, get_dataset_spec, get_model_spec, load_registry


def test_resource_registry_loads_local_model_and_dataset():
    registry = load_registry()
    model = get_model_spec("local_rule_based", registry)
    dataset = get_dataset_spec("codefixer_toy", registry)
    assert model["policy_type"] == "rule_based"
    assert dataset["task_file"] == "configs/tasks_toy.yaml"
    assert dataset["local_available"] is True


def test_apply_resource_selection_builds_runnable_config():
    config = load_yaml("configs/local_mini_test.yaml")
    merged = apply_resource_selection(config, dataset_name="codefixer_toy", model_name="local_rule_based")
    assert merged["paths"]["tasks_file"] == "configs/tasks_toy.yaml"
    assert merged["policy"]["type"] == "rule_based"
    assert merged["selected_resources"]["dataset_name"] == "codefixer_toy"
    assert merged["selected_resources"]["model_name"] == "local_rule_based"


def test_registry_contains_final_experiment_resources():
    registry = load_registry()
    assert "qwen3_coder_30b_a3b_vllm" in registry["models"]
    assert "defects4j_active" in registry["datasets"]
