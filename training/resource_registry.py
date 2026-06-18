"""Central registry for datasets and model endpoints used by CodeFixer."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from env.task_loader import load_yaml


def load_registry(
    models_path: str | Path = "configs/models.yaml",
    datasets_path: str | Path = "configs/datasets.yaml",
) -> dict[str, dict[str, Any]]:
    """Load model and dataset registries from YAML files."""

    models = load_yaml(models_path).get("models", {})
    datasets = load_yaml(datasets_path).get("datasets", {})
    if not isinstance(models, dict) or not isinstance(datasets, dict):
        raise ValueError("Registry files must contain mapping fields named models and datasets.")
    return {"models": models, "datasets": datasets}


def get_model_spec(name: str, registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return one model spec by registry name."""

    registry = registry or load_registry()
    try:
        spec = registry["models"][name]
    except KeyError as exc:
        raise KeyError(f"Unknown model '{name}'. Available: {sorted(registry['models'])}") from exc
    return deepcopy(spec)


def get_dataset_spec(name: str, registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return one dataset spec by registry name."""

    registry = registry or load_registry()
    try:
        spec = registry["datasets"][name]
    except KeyError as exc:
        raise KeyError(f"Unknown dataset '{name}'. Available: {sorted(registry['datasets'])}") from exc
    return deepcopy(spec)


def apply_resource_selection(config: dict[str, Any], dataset_name: str | None = None, model_name: str | None = None) -> dict[str, Any]:
    """Merge selected dataset/model registry entries into a runnable evaluation config."""

    config = deepcopy(config)
    selection = config.get("resource_selection", {})
    dataset_key = dataset_name or selection.get("dataset", "codefixer_toy")
    model_key = model_name or selection.get("model", "local_rule_based")
    registry = load_registry()
    dataset = get_dataset_spec(dataset_key, registry)
    model = get_model_spec(model_key, registry)

    task_file = dataset.get("task_file")
    if not task_file:
        raise ValueError(f"Dataset '{dataset_key}' does not define a local task_file; it is probably server-only.")
    config.setdefault("paths", {})["tasks_file"] = str(task_file)

    config.setdefault("policy", {})["type"] = model.get("policy_type", "rule_based")
    if model.get("policy_type") == "llm":
        provider = "openai" if model.get("provider") == "openai" else "local"
        config["llm"] = {
            "provider": provider,
            "model": model.get("model_name", model_key),
            "endpoint": model.get("endpoint", ""),
            "max_tokens": int(model.get("max_tokens", 800)),
            "temperature": float(model.get("temperature", 0.0)),
            "api_key_env": model.get("api_key_env", "OPENAI_API_KEY"),
        }
    else:
        config["llm"] = {
            "provider": "internal",
            "model": model.get("model_name", model_key),
            "endpoint": "",
            "max_tokens": 0,
            "temperature": 0.0,
        }

    config["selected_resources"] = {
        "dataset_name": dataset_key,
        "dataset": dataset,
        "model_name": model_key,
        "model": model,
    }
    return config


def registry_summary(registry: dict[str, dict[str, Any]] | None = None) -> str:
    """Render a compact Markdown summary of registered models and datasets."""

    registry = registry or load_registry()
    lines = ["# CodeFixer Resource Registry", "", "## Models", ""]
    for name, spec in registry["models"].items():
        lines.append(f"- `{name}`: {spec.get('display_name', name)}; provider={spec.get('provider')}; server_only={spec.get('server_only')}")
    lines.extend(["", "## Datasets", ""])
    for name, spec in registry["datasets"].items():
        lines.append(f"- `{name}`: {spec.get('display_name', name)}; task_format={spec.get('task_format')}; server_only={spec.get('server_only')}")
    return "\n".join(lines) + "\n"
