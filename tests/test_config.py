from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codefixer_baseline.config import load_json, load_yaml


def test_load_yaml_config() -> None:
    data = load_yaml(ROOT / "configs" / "qwen3_vllm_mini_swe.yaml")
    assert data["model"]["model_name"] == "hosted_vllm/qwen3-coder-30b-a3b"
    assert data["model"]["model_kwargs"]["api_base"] == "http://127.0.0.1:8001/v1"
    assert data["agent"]["step_limit"] == 80


def test_load_litellm_registry() -> None:
    data = load_json(ROOT / "configs" / "litellm_registry.json")
    assert data["qwen3-coder-30b-a3b"]["litellm_provider"] == "hosted_vllm"
