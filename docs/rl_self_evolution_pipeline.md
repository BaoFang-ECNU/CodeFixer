# 强化学习与自进化数据闭环

当前版本实现的是 **RLVR 数据闭环**，不是本地大模型训练。

## 本地 smoke

```bash
python scripts/run_local_rl_smoke.py
```

默认使用：

```text
dataset = codefixer_toy
model = local_rule_based
max_tasks = 2
mode = export_only
```

输出目录：

```text
outputs/local_rl_smoke/
```

关键产物：

```text
outputs/local_rl_smoke/training/sft_train.jsonl
outputs/local_rl_smoke/training/dpo_train.jsonl
outputs/local_rl_smoke/training/opd_train.jsonl
outputs/local_rl_smoke/training/rwr_train.jsonl
outputs/local_rl_smoke/training/rlvr_rollouts.jsonl
outputs/local_rl_smoke/training/guidance_train.jsonl
outputs/local_rl_smoke/training/evolution_report.md
```

## 服务器训练模板

```bash
python scripts/server_train_qwen.py --config configs/training_pipeline.yaml
```

该脚本只检查模型与数据集配置，并输出服务器训练步骤，不会在本地启动训练。

目标模型：

```text
qwen2_5_coder_7b
```

## 训练路线

```text
SFT 冷启动
-> DPO 偏好学习
-> OPD 自蒸馏
-> RWR 轻量策略更新
-> RLVR 服务器训练
```

## Guidance 格式

```json
{
  "failure_summary": "补丁后测试仍失败",
  "suspected_bug_type": "off_by_one",
  "suggested_next_action": "inspect_or_edit_target_file",
  "repair_hint": "检查循环、切片或 range 边界是否少包含一个元素。",
  "risk_flags": [],
  "reward": 0.94
}
```
