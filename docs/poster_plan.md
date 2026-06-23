# CodeFixer-Evolve Poster 制作说明

本文档用于指导合作者制作课程 poster。当前版本对应最终 held-out Django50 实验结果，重点展示：从 baseline 到 feedback/memory、online bandit，再到 semantic/pairwise candidate selector 的逐步提升。

## 1. Poster 核心叙事

一句话版本：

> CodeFixer-Evolve 在不微调基础 LLM 的情况下，通过过程记忆、prompt-policy bandit 和语义候选选择，将 SWE-bench Lite Django held-out 任务的 selected pass@1 从 22% 提升到 42%。

推荐标题：

```text
CodeFixer-Evolve: 基于反馈记忆、Prompt-Policy Bandit 与语义候选选择的代码修复智能体
```

推荐副标题：

```text
在 SWE-bench Lite Django held-out 任务上的自进化代码修复实验
```

最重要的三条结论：

- Baseline raw 在 held-out Django50 上为 `11/50 = 22%`。
- V4 global bandit no-memory selected 达到 `18/50 = 36%`，candidate oracle pass@k 达到 `24/50 = 48%`，说明主要瓶颈转向候选选择。
- V5 semantic-pairwise blended selector 达到 `21/50 = 42%`，在保持 unsafe edit rate 为 `10%` 的同时缩小 selection gap。

## 2. 方法概览

建议把方法画成一张横向流程图：

```text
Issue + Repository
  -> mini-SWE-agent / Qwen3-Coder
  -> Multiple candidate patches
  -> Patch audit + visible feedback
  -> Prompt-policy controller
  -> Candidate pool
  -> Semantic / pairwise judge
  -> Final selected patch
```

三个核心模块：

1. Process Memory
   从历史失败轨迹中总结任务无关的过程规则，例如避免编辑测试、避免临时复现工程、避免 `.orig/.backup/.fixed` 文件、优先 source-only patch。

2. Prompt-Policy Bandit
   将不同 prompt policy 视作 bandit arms，用 Thompson Sampling 根据 patch apply、visible pass、compliance、unsafe edit 等代理 reward 在线选择下一轮生成策略。

3. Semantic-Pairwise Candidate Selector
   固定已有 candidate pool，不重新生成 patch。使用 LLM judge 对候选进行语义正确性评分和同任务 pairwise 比较，再与 test-aware / safety features 融合选择最终候选。

## 3. 实验设置

数据：

- SWE-bench Lite Django held-out 50 tasks。
- 这 50 个实例与早期 Django-44 development slice 分离，用于更严格的 sanity validation。

模型与执行：

- Base LLM: Qwen3-Coder-30B-A3B via vLLM。
- Agent: mini-SWE-agent。
- 本地 evaluator 运行 patch apply、fix tests、regression tests、hidden test patch 等。
- 本项目不做 LoRA/PPO/GRPO 参数微调，主要使用 lightweight online bandit 与离线 selector/reranker。

## 4. 主要结果

### 4.1 Held-out Django50 主结果

建议做成主柱状图。

| System | Selected pass@1 |
|---|---:|
| V1 raw baseline | 11/50 = 0.22 |
| V3 memory | 14/50 = 0.28 |
| V3 static4 | 15/50 = 0.30 |
| V4 global bandit no-memory | 18/50 = 0.36 |
| V5 semantic-pairwise blended selector | 21/50 = 0.42 |

建议图标题：

```text
Held-out Django50: semantic candidate selection closes half of the selection gap
```

### 4.2 Candidate pool 与 selection gap

建议做成 pass@1 vs oracle pass@k 对比图。

| System | Selected pass@1 | Candidate oracle pass@k |
|---|---:|---:|
| V4 global no-memory | 18/50 = 0.36 | 24/50 = 0.48 |
| V4 global + memory candidates | N/A | 21/50 = 0.42 |
| V5 blended selector | 21/50 = 0.42 | same pool upper bound 24/50 = 0.48 |

解释文字：

```text
The no-memory global bandit candidate pool contains correct candidates for 24/50 tasks, but the original selector chooses correct patches for only 18/50. The V5 blended selector recovers 3 of the 6 missed tasks.
```

中文解释：

```text
候选池已经包含 24 个可通过任务，但原 selector 只选中 18 个。V5 blended selector 将正确选择数提升到 21 个，说明瓶颈已经从单纯生成转向候选选择。
```

### 4.3 Selector 消融

建议做成表格或小柱状图。

| Selector | Pass@1 | Regression pass | Compliance | Unsafe edit | Avg patch lines |
|---|---:|---:|---:|---:|---:|
| Original / anchor | 18/50 = 0.36 | 0.7872 | 0.70 | 0.10 | 12.98 |
| Test-aware rules | 18/50 = 0.36 | 0.7872 | 0.70 | 0.10 | 12.98 |
| Semantic judge | 20/50 = 0.40 | 0.7447 | 0.54 | 0.30 | 155.84 |
| Pairwise judge | 19/50 = 0.38 | 0.8085 | 0.46 | 0.24 | 84.24 |
| Blended selector | 21/50 = 0.42 | 0.8085 | 0.64 | 0.10 | 23.80 |
| Calibrated selector | 20/50 = 0.40 | 0.8298 | 0.70 | 0.10 | 15.66 |

重点解释：

```text
Rule-only and calibrated-without-judge features do not improve over the original selector. LLM semantic and pairwise signals provide new correctness information. The blended selector improves accuracy while keeping unsafe edit rate unchanged.
```

### 4.4 Compliance 与 safety

建议用 grouped bar chart。

| System | Compliance | Unsafe edit | Empty patch | Artifact exposure | Avg patch lines |
|---|---:|---:|---:|---:|---:|
| V1 raw baseline | 0.24 | 0.40 | 0.14 | 0.04 | 332.20 |
| V3 memory | 0.74 | 0.14 | 0.00 | 0.00 | 451.96 |
| V4 global no-memory | 0.70 | 0.10 | 0.00 | 0.00 | 12.98 |
| V5 blended selector | 0.64 | 0.10 | 0.00 | 0.00 | 23.80 |

可放在 poster 上的突出数字：

```text
Pass@1: 22% -> 42%
Unsafe edit: 40% -> 10%
Oracle pass@k: 48%
```

## 5. 负结果与诊断

这部分适合放在右下角，体现研究过程不是单纯堆技巧。

### 5.1 Memory-only safety reranking 过于保守

Safe-final penalty curve 显示：

```text
penalty_scale = 0 ... 8
pass@1 始终为 16/50 = 0.32
regression_pass 为 0.8298
```

解释：

```text
The degradation is driven by the conservative safe-final base policy, not by the memory penalty magnitude. Memory is useful as a safety prior, but should not replace an accuracy-oriented selector.
```

### 5.2 更复杂的 context / hierarchical bandit 不一定更好

在小样本、弱 reward 场景下，contextual bandit 和 HierTS-lite 更容易变保守或拟合噪声。最终主线选择 global bandit + semantic selector，而不是更复杂的 posterior 结构。

## 6. 建议 Poster 图表清单

1. 系统流程图
   展示 mini-SWE-agent、candidate pool、bandit controller、semantic/pairwise selector。

2. Held-out Django50 pass@1 主图
   V1 raw -> V3 memory -> V3 static4 -> V4 global -> V5 blended。

3. Candidate pool selection gap 图
   V4 selected 18/50, oracle 24/50, V5 blended 21/50。

4. Selector ablation 表
   Original / semantic / pairwise / blended / calibrated。

5. Safety-compliance 图
   Compliance、unsafe edit、empty patch、artifact exposure。

6. 负结果小图或小表
   safe-final penalty curve，说明 safety-first replacement selector 会过保守。

## 7. 数据文件位置

本仓库中已经包含最终实验数据包：

```text
report_final_artifacts/
```

关键文件：

```text
report_final_artifacts/metrics/
report_final_artifacts/selectors/selector_summary.csv
report_final_artifacts/selectors/selected_blended.csv
report_final_artifacts/judge/semantic_scores.jsonl
report_final_artifacts/judge/pairwise_scores.jsonl
report_final_artifacts/diagnostics/safe_final_penalty_curve.csv
report_final_artifacts/diagnostics/memory_tiebreaker_curve.csv
```

原始压缩包也保留在仓库根目录：

```text
report_final_artifacts_20260623_072542.tar.gz
```

## 8. 报告/Poster 中应避免的表述

不要写：

```text
我们通过强化学习微调了 LLM。
```

建议写：

```text
我们没有微调基础 LLM，而是使用 reinforcement-learning-style prompt-policy bandit 在线选择 prompt arms，并使用 semantic/pairwise judge 进行离线候选选择。
```

不要写：

```text
memory 一定能提升 accuracy。
```

建议写：

```text
memory 更像 safety/compliance prior；在当前 held-out 结果中，no-memory global bandit 产生更高 oracle pass@k，而 memory-guided candidates 更合规、更安全。
```

不要写：

```text
V5 已经达到 oracle。
```

建议写：

```text
V5 将 selected pass@1 从 18/50 提升到 21/50，缩小了一半 selection gap；candidate oracle 仍为 24/50，说明 selector 仍有改进空间。
```

## 9. 推荐最终摘要

```text
CodeFixer-Evolve studies code-repair improvement without fine-tuning the base LLM. On a disjoint held-out Django50 subset from SWE-bench Lite, raw mini-SWE-agent achieves 11/50 pass@1. Feedback memory and static multi-candidate selection improve this to 15/50, while a global Thompson-sampling prompt controller reaches 18/50. The candidate pool oracle reaches 24/50, revealing candidate selection as the main bottleneck. By adding semantic LLM judging and pairwise candidate comparison, our blended selector improves pass@1 to 21/50 while preserving the unsafe edit rate at 10%.
```
