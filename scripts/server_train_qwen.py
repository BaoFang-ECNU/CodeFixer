#!/usr/bin/env python
"""Print a server-side Qwen training plan from the CodeFixer registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.task_loader import load_yaml
from training.resource_registry import get_dataset_spec, get_model_spec


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate server training config and print command templates.")
    parser.add_argument("--config", default="configs/training_pipeline.yaml")
    args = parser.parse_args()

    config = load_yaml(args.config)
    training = config.get("training", {})
    target_model = training.get("target_model", "qwen2_5_coder_7b")
    dataset = training.get("dataset", "codefixer_toy")
    model_spec = get_model_spec(target_model)
    dataset_spec = get_dataset_spec(dataset)
    payload = {
        "status": "template_only",
        "message": "本地不执行真实训练；请在服务器上使用这些配置和导出的 JSONL 数据启动 SFT/DPO/OPD/RLVR。",
        "target_model": target_model,
        "model_spec": model_spec,
        "dataset": dataset,
        "dataset_spec": dataset_spec,
        "expected_inputs": [
            "training/sft_train.jsonl",
            "training/dpo_train.jsonl",
            "training/opd_train.jsonl",
            "training/rwr_train.jsonl",
            "training/rlvr_rollouts.jsonl",
            "training/guidance_train.jsonl",
        ],
        "server_steps": [
            "1. 将 JSONL 数据同步到训练服务器。",
            "2. 启动 Qwen2.5-Coder-7B 的 SFT 训练。",
            "3. 用 DPO chosen/rejected 数据进行偏好学习。",
            "4. 用 OPD/RWR/RLVR 数据做后续策略改进实验。",
            "5. 回到 CodeFixer 运行 SWE-bench Lite/Verified 评测。",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
