# CodeFixer 最终实验计划

## 目标

最终版本采用：

```text
SWE-bench Lite 训练/开发
Defects4J Java 测试
Qwen3-30B 教师与强基线
Qwen2.5-Coder-7B 或同级学生模型训练
```

核心目标不是只证明 toy task 能跑通，而是验证代码修复 Agent 是否能从环境反馈、测试结果和历史轨迹中形成可复用的修复策略。

## 数据集划分

- `CodeFixer benchmark`：本地 smoke test、调试、消融快速验证。
- `SWE-bench Lite train/dev`：生成 teacher rollout、SFT、DPO、OPD、RWR、RLVR 数据。
- `Defects4J active bugs`：Java 代码修复最终测试集，默认不进入训练。
- `SWE-bench Verified / holdout`：Python repo-level 补充测试集。

注意：如果 SWE-bench Lite 用于训练，就不能再把同一批任务作为最终泛化结论。

## 系统版本

- `RuleBaseline`：规则 Agent。
- `QwenDirect`：Qwen3-30B 单轮工具动作或补丁生成。
- `QwenFeedbackAgent`：Qwen3-30B + ACI + 测试反馈 + 多轮工具调用。
- `LearningAgent`：学生模型经过 SFT/DPO/OPD/RWR/RLVR 数据训练后运行。
- `LearningAgent+Memory`：在 LearningAgent 上加入长期记忆和失败轨迹总结。

## 关键命令

本地验证：

```bash
python scripts/run_local_mini_test.py
python scripts/run_local_rl_smoke.py
python -m pytest tests -q
```

Qwen3-30B endpoint 验证：

```bash
python -m evaluation.evaluate --config configs/qwen3_local_eval.yaml --max-tasks 3
```

SWE-bench Lite 训练数据准备：

```bash
python scripts/prepare_swebench_lite.py --source hf --split train --max-instances 50
python scripts/export_training_data.py --config configs/training_pipeline_swebench.yaml
```

Defects4J 测试准备：

```bash
python scripts/prepare_defects4j.py --projects Lang,Chart,Math --max-bugs 10 --check-env
python -m evaluation.evaluate --config configs/defects4j_eval.yaml --max-tasks 10
```

最终对比与消融：

```bash
python -m evaluation.compare_systems --config configs/final_eval.yaml
python -m evaluation.ablation --config configs/final_eval.yaml
python scripts/summarize_final_experiment.py --root outputs/final_experiments
```

## 必报指标

- Pass@1
- Pass@k
- Visible Test Pass Rate
- Hidden/Regression Test Pass Rate
- Average Tool Calls
- Average Test Runs
- Patch Size
- Patch File Count
- Unsafe Edit Rate
- Runtime / Cost
- Java compile failure rate
- Defects4J triggering test pass rate
- SFT/DPO/OPD/RWR/RLVR 数据量

## 服务器环境

Defects4J 建议在 Linux 服务器运行，需要：

```text
Java 11
Git
Subversion
Perl
cpanm
Defects4J
TZ=America/Los_Angeles
```

Qwen3-30B 建议通过 vLLM 暴露 OpenAI-compatible endpoint：

```text
http://127.0.0.1:8001/v1/chat/completions
```

4 张 4090 主要用于 Qwen3-30B 推理、teacher rollout 和 7B 学生模型 LoRA/QLoRA 训练，不建议做 30B 全参数微调。

