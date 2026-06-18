# 模型与数据集注册表

CodeFixer 现在用两个配置文件统一管理数据集和模型：

- `configs/datasets.yaml`
- `configs/models.yaml`

## 本地可运行资源

本地默认使用：

```text
dataset = codefixer_toy
model = local_rule_based
```

它不需要 GPU、不需要服务器、不需要 API key，适合验证代码流程是否能跑通。

运行：

```bash
python scripts/run_local_mini_test.py
```

输出：

```text
outputs/local_mini_test/results.json
outputs/local_mini_test/summary.md
outputs/local_mini_test/trajectory.jsonl
outputs/local_mini_test/selected_resources.json
```

也可以指定轻量 benchmark：

```bash
python scripts/run_local_mini_test.py --dataset codefixer_benchmark --model local_rule_based --max-tasks 3
```

## 服务器训练资源

服务器侧优先模型：

```text
qwen2_5_coder_7b
```

用途：

```text
SFT -> DPO -> OPD -> RLVR
```

服务器强 baseline：

```text
qwen3_coder_30b_a3b_vllm
```

它对应 ytc 分支中的 mini-SWE-agent + Qwen3-Coder-30B-A3B-Instruct 路线。

## 推荐数据集路线

本地：

```text
codefixer_toy
codefixer_benchmark
```

服务器训练：

```text
HumanEvalFix
SWE-smith
SWE-Gym
BugsInPy / QuixBugs / Defects4J
```

最终评测：

```text
SWE-bench Lite
SWE-bench Verified
```

原则：

> SWE-bench Lite / Verified 尽量保留为评测集，避免过早混入训练造成数据污染。
