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
        "message": "本脚本只做服务器训练配置检查，不在本地启动真实训练；请在 4x4090 服务器上使用导出的 JSONL 数据启动 SFT/DPO/OPD/RWR/RLVR。",
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
            "1. 使用 Qwen3-30B 作为教师模型生成 SWE-bench Lite rollouts。",
            "2. 将 SFT/DPO/OPD/RWR/RLVR JSONL 数据同步到训练服务器。",
            "3. 对 Qwen2.5-Coder-7B 或同级学生模型执行 LoRA/QLoRA SFT。",
            "4. 使用 DPO chosen/rejected 数据做偏好学习。",
            "5. 使用 OPD/RWR/RLVR 数据做后续策略改进实验。",
            "6. 回到 CodeFixer 运行 Defects4J、SWE-bench Verified 或 holdout 评测。",
        ],
        "suggested_commands": [
            "python scripts/prepare_swebench_lite.py --source hf --split train --max-instances 50",
            "python scripts/export_training_data.py --config configs/training_pipeline_swebench.yaml",
            "python scripts/prepare_defects4j.py --projects Lang,Chart,Math --max-bugs 10 --check-env",
            "python -m evaluation.compare_systems --config configs/final_eval.yaml",
            "python scripts/summarize_final_experiment.py --root outputs/final_experiments",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

