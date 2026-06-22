# CodeFixer-Evolve Poster 制作说明

本文档用于指导合作者制作课程 poster。目标是把 CodeFixer-Evolve 的方法、主要实验、held-out 验证和结论压缩成一张清晰的学术海报。

## 1. Poster 核心叙事

一句话版本：

> CodeFixer-Evolve 在不微调基础 LLM 的情况下，通过历史反馈记忆、Prompt-Policy Thompson Sampling 和合规感知候选重排，提高 SWE-bench Lite Django 代码修复任务的通过率、合规性和安全性。

最重要的结果：

- Django-44 development slice 上，V4 global bandit 的 candidate pass@k 达到 `16/44`，是当前最高候选池上限。
- Disjoint held-out Django50 上，selected pass@1 从 raw baseline 的 `11/50` 提升到 V4 global 的 `17/50`。
- Held-out Django50 上，submission compliance 从 `24%` 提升到 `80%`，unsafe edit rate 从 `40%` 降到 `10%`。

建议 poster 标题：

```text
CodeFixer-Evolve: 基于反馈记忆与 Prompt-Policy Bandit 的代码修复智能体
```

可选副标题：

```text
在 SWE-bench Lite Django 任务上的自进化代码修复实验
```

## 2. 推荐版面结构

如果是横版 poster，建议三栏：

### 左栏：问题与方法

- 研究问题
- CodeFixer-Evolve 总体流程图
- 三个核心模块：Process Memory、Prompt-Policy Bandit、Candidate Reranker

### 中栏：Django-44 开发集结果

- pass@1 / pass@k 对比图
- 合规性与安全性对比图
- 消融实验结论

### 右栏：Disjoint Held-out Django50 泛化验证

- held-out pass@1 主结果图
- held-out compliance / unsafe 对比图
- 关键发现、负结果和未来工作

底部可以放 GitHub / 代码 / 数据说明。

## 3. 可直接放进 Poster 的文字

### 3.1 研究问题

```text
大模型代码修复 Agent 经常生成格式不合规、修改测试文件、临时文件泄露或过大的 patch。单次 prompt 改进难以稳定提升后续任务表现。本项目研究：能否利用历史修复轨迹中的反馈，进化出更可靠、更合规的代码修复策略？
```

更正式版本：

```text
目标：在不微调基础 LLM 参数的前提下，通过外层过程记忆、候选重排和 prompt-policy controller，提高 SWE-bench 风格代码修复 Agent 的通过率与提交合规性。
```

### 3.2 方法概述

```text
CodeFixer-Evolve 使用 mini-SWE-agent 与 Qwen3-Coder 生成候选补丁，并通过本地执行反馈、patch 合规检查和历史轨迹记忆进行自进化。系统从上一轮候选轨迹中提炼任务无关的 process memory，用 Thompson Sampling 在多个 prompt policy arm 之间进行选择，并用合规感知 reranker 从多个候选补丁中选择最终提交。
```

### 3.3 三个核心模块

```text
Process Memory：从历史失败轨迹中总结任务无关的修复规范，例如避免编辑 tests、避免生成临时复现文件、避免 .orig/.backup/.fixed 文件、优先 source-only patch。

Prompt-Policy Bandit：将不同修复策略 prompt 视作 bandit arms，用本地执行反馈和合规信号更新 Beta posterior。

Candidate Reranker：综合 patch apply、fix/regression tests、submission compliance、unsafe edit、patch size 等指标选择最终补丁。
```

### 3.4 关键发现

```text
1. Evolution memory 在 held-out Django50 上将 selected pass@1 从 11/50 提升到 14/50。
2. V4 global Thompson Sampling 进一步提升到 17/50，并显著改善提交合规性。
3. Django-44 上 V4 global bandit 的 candidate pass@k 达到 16/44，但 selected pass@1 为 12/44，说明候选选择仍是主要瓶颈。
4. HierTS-lite 在本实验规模下没有带来收益，说明小样本弱 reward 场景中复杂后验容易过拟合噪声。
```

### 3.5 结论

```text
CodeFixer-Evolve 在不微调 LLM 的情况下，通过历史反馈记忆、prompt-policy bandit 和合规感知重排，在 disjoint held-out Django50 上将 selected pass@1 从 22% 提升到 34%，并将 submission compliance 从 24% 提升到 80%。
```

## 4. 需要制作的图表

### 图 1：系统流程图

用途：展示 CodeFixer-Evolve pipeline。

建议画成横向流程：

```text
Issue + Repo
   ↓
mini-SWE-agent / Qwen3-Coder
   ↓
Candidate patches
   ↓
Local feedback + Patch audit
   ↓
Process Memory + Prompt-Policy Bandit
   ↓
Compliance-aware Reranker
   ↓
Final selected patch
```

图中突出三个彩色模块：

- Process Memory
- Thompson Sampling Prompt Controller
- Candidate Reranker

### 图 2：Django-44 pass@1 / pass@k 对比柱状图

用途：展示开发集上方法迭代和候选池上限。

推荐数据：

| System | selected pass@1 | candidate pass@k |
|---|---:|---:|
| Baseline raw | 9/44 | 9/44 |
| V3 memory | 12/44 | 12/44 |
| V3 static4 | 7/44 | 14/44 |
| V4 global bandit | 12/44 | 16/44 |
| V4 contextual bandit | 11/44 | 15/44 |
| HierTS tau=3 | 9/44 | 13/44 |
| HierTS tau=10 | 10/44 | 12/44 |

建议标题：

```text
Django-44: Global bandit achieves the best candidate pool quality
```

### 图 3：Django-44 合规性与安全性对比

用途：展示从 raw baseline 到 V4 global 的安全性提升。

推荐只放三组，避免太乱：

| System | Compliance ↑ | Unsafe ↓ | Empty ↓ | Artifact ↓ | Avg Patch Lines ↓ |
|---|---:|---:|---:|---:|---:|
| Baseline raw | 13.64% | 72.73% | 2.27% | 4.55% | 502.36 |
| V3 memory | 52.27% | 15.91% | 2.27% | 0% | 230.52 |
| V4 global | 75.00% | 11.36% | 0% | 0% | 178.27 |

建议画法：

- 左侧：Compliance 柱状图。
- 右侧：Unsafe / Empty / Artifact 降低图。
- patch lines 可以做小条形图或直接标注。

### 图 4：Disjoint Held-out Django50 selected pass@1

用途：最重要的泛化验证图。

推荐数据：

| System | selected pass@1 |
|---|---:|
| V1 raw | 11/50 |
| V3 memory | 14/50 |
| V4 global | 17/50 |

建议标题：

```text
Held-out Django50: improvements transfer beyond the development slice
```

### 图 5：Held-out Django50 合规性与安全性

推荐数据：

| System | Compliance ↑ | Unsafe ↓ | Empty ↓ | Artifact ↓ | Avg Patch Lines ↓ |
|---|---:|---:|---:|---:|---:|
| V1 raw | 24% | 40% | 14% | 4% | 332.2 |
| V3 memory | 74% | 14% | 0% | 0% | 451.96 |
| V4 global | 80% | 10% | 2% | 0% | 148.66 |

建议强调：

```text
Compliance: 24% → 80%
Unsafe edits: 40% → 10%
```

### 表 1：Prompt Arms 说明

| Prompt Arm | 目的 |
|---|---|
| `v3_control` | 标准反馈修复 |
| `minimal_patch` | 优先小而集中的 source-only patch |
| `failing_test_first` | 根据失败测试定位修复 |
| `regression_conservative` | 避免破坏已有行为 |
| `localization_first` | 先定位真实代码 owner |
| `traceback_api_contract` | 修复 API / contract 类错误 |

## 5. Poster 需要的实验结果文件

### 必须下载 / 保留

这些文件足够支持 poster 的主要图表。

#### Django-44 开发集关键结果

从服务器下载：

```text
outputs/summary/final_key_metrics.csv
outputs/summary/final_failure_taxonomy.txt
outputs/summary/ablation_reranker.md
```

如果 `final_key_metrics.csv` 不完整，再下载这些目录中的 `system_metrics.csv` 和 `system_metrics.md`：

```text
outputs/local_eval_old9_raw_probe/
outputs/local_eval_feedback_v3_django44/
outputs/local_eval_feedback_v3_candidates_django44/
outputs/local_eval_feedback_v3_static4_django44/
outputs/local_eval_feedback_v3_static4_candidates_django44/
outputs/local_eval_feedback_v4_bandit_django44/
outputs/local_eval_feedback_v4_bandit_candidates_django44/
outputs/local_eval_feedback_v4_contextual_django44/
outputs/local_eval_feedback_v4_contextual_candidates_django44/
outputs/local_eval_feedback_v4_hier_django44/
outputs/local_eval_feedback_v4_hier_candidates_django44/
outputs/local_eval_feedback_v4_hier_tau10_django44/
outputs/local_eval_feedback_v4_hier_tau10_candidates_django44/
```

#### Held-out Django50 结果

从服务器下载：

```text
outputs/summary/heldout/heldout_key_metrics.csv
outputs/summary/heldout/v1_raw/system_metrics.csv
outputs/summary/heldout/v1_raw/system_metrics.md
outputs/summary/heldout/v3_memory/system_metrics.csv
outputs/summary/heldout/v3_memory/system_metrics.md
outputs/summary/heldout/v4_global/system_metrics.csv
outputs/summary/heldout/v4_global/system_metrics.md
```

如果还没复制回 HDD，原始位置是：

```text
/inspire/ssd/project/machine-behavior/czxs25150055/codefixer_eval_outputs/local_eval_heldout_v3_memory_django50/system_metrics.*
/inspire/ssd/project/machine-behavior/czxs25150055/codefixer_eval_outputs/local_eval_heldout_v4_global_django50/system_metrics.*
```

#### 可选：用于 qualitative case 的 patch

如果 poster 想放一个成功修复案例，可以下载：

```text
outputs/local_runs/heldout_v4_global_django50/<某个成功 task>/candidate_0/patch.diff
outputs/local_runs/heldout_v4_global_django50/<某个成功 task>/candidate_0/metadata.json
```

推荐从 held-out V4 成功任务里挑一个，例如：

```text
django__django-13447
django__django-13551
django__django-13658
django__django-13925
django__django-14017
django__django-14238
django__django-14382
django__django-14580
django__django-14608
django__django-14672
django__django-14752
django__django-14855
django__django-14915
django__django-15498
django__django-15789
django__django-15790
django__django-15814
```

## 6. 推荐从服务器打包下载的命令

在服务器上执行：

```bash
cd /inspire/hdd/project/machine-behavior/czxs25150055/codefixer-baseline

mkdir -p poster_artifacts

cp -r outputs/summary poster_artifacts/

# 可选：如果想放成功案例 patch，复制几个 patch。
mkdir -p poster_artifacts/examples
for iid in django__django-13447 django__django-14238 django__django-15814; do
  mkdir -p "poster_artifacts/examples/$iid"
  cp "outputs/local_runs/heldout_v4_global_django50/$iid/candidate_0/patch.diff" \
     "poster_artifacts/examples/$iid/" 2>/dev/null || true
  cp "outputs/local_runs/heldout_v4_global_django50/$iid/candidate_0/metadata.json" \
     "poster_artifacts/examples/$iid/" 2>/dev/null || true
done

tar -czf poster_artifacts_codefixer_$(date +%Y%m%d_%H%M%S).tar.gz poster_artifacts
ls -lh poster_artifacts_codefixer_*.tar.gz
```

如果 `outputs/summary/heldout` 还没有包含 SSD 上的 V3/V4 held-out 文件，先执行：

```bash
mkdir -p outputs/summary/heldout/v3_memory
mkdir -p outputs/summary/heldout/v4_global

cp /inspire/ssd/project/machine-behavior/czxs25150055/codefixer_eval_outputs/local_eval_heldout_v3_memory_django50/system_metrics.* \
   outputs/summary/heldout/v3_memory/

cp /inspire/ssd/project/machine-behavior/czxs25150055/codefixer_eval_outputs/local_eval_heldout_v4_global_django50/system_metrics.* \
   outputs/summary/heldout/v4_global/
```

## 7. 需要避免的表述

不要写：

```text
我们严格证明了跨仓库泛化。
```

建议写：

```text
我们在 Django-44 development slice 上完成方法开发和消融，并在 disjoint Django50 上进行 held-out sanity validation。结果表明，最终方法在未参与方法选择的 Django 实例上仍能提升 selected pass@1 和 patch 合规性。
```

不要把 held-out candidate pass@k 作为主指标，因为 held-out candidates eval 受存储配额限制没有稳定完成。Poster 中可写：

```text
Full candidate pass@k is reported on Django-44 development experiments. Held-out Django50 reports selected pass@1 due to storage constraints during full candidate evaluation.
```

如果空间有限，也可以不提这句，只在图上不放 held-out pass@k。

## 8. 最终推荐重点数字

Poster 上建议突出显示三个大数字：

```text
Django-44 candidate pass@k: 16/44
Held-out pass@1: 11/50 → 17/50
Held-out compliance: 24% → 80%
```

辅助数字：

```text
Held-out unsafe edit: 40% → 10%
Django-44 V4 global compliance: 75%
Django-44 V4 global unsafe edit: 11.36%
```

