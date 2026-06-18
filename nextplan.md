# CodeFixer 下一阶段规划

## 1. 当前阶段结论

我们已经完成了 CodeFixer 的初始工程闭环，也研读了 SWE-Agent、SGAgent 和 CodeR 三篇代表性工作。

下一阶段的目标不是简单增加规则，而是把项目升级为：

```text
SWE-Agent 风格工具接口
+ SGAgent 风格多智能体协作
+ CodeR 风格任务图调度
+ Qwen Coder 2.5 7B 代码修复训练
+ 测试反馈驱动的自进化
```

一句话目标：

> 让 CodeFixer 从“能跑 toy repair 的规则 Agent”，升级为“可产生训练数据、可微调小模型、可扩展到真实仓库修复任务的研究型系统”。

## 2. SWE-Agent 的核心启发

SWE-Agent 的重点不是多智能体，而是 **Agent-Computer Interface，简称 ACI**。

也就是说，它认为代码修复 Agent 的能力不只取决于大模型本身，还取决于模型能不能使用一套清晰、稳定、容易理解的工具。

SWE-Agent 的核心设计包括：

- `find_file`：按文件名查找文件。
- `search_file` / `search_dir`：在文件或目录中搜索关键词。
- `open` / `goto` / `scroll`：按窗口查看代码，而不是一次塞入整个文件。
- `edit`：按行编辑代码，并在编辑后展示结果。
- `lint guardrail`：如果编辑引入语法错误，就自动拒绝并反馈错误。
- `run tests`：通过测试结果判断修复是否有效。
- `submit`：最终提交补丁。

SWE-Agent 给我们的主要启发：

1. **工具接口要简单**
   工具越复杂，模型越容易调用失败。

2. **反馈要短而有用**
   不要把完整文件、完整日志、完整历史都塞给模型。

3. **编辑后要立刻展示结果**
   让 Agent 看到自己刚刚改了什么。

4. **必须有安全护栏**
   语法错误、测试删除、越权修改、硬编码答案，都应该被拦截或惩罚。

5. **代码修复是一个多步过程**
   典型流程是：

```text
理解 issue -> 搜索定位 -> 查看代码 -> 编辑 -> 测试 -> 根据反馈再修复 -> 提交
```

## 3. SGAgent 的核心启发

SGAgent 的重点是 **Suggestion-Guided Multi-Agent Repair**。

它认为传统代码修复常见问题是：

```text
定位到了 bug 位置，但不知道应该怎么修
```

所以 SGAgent 把流程从：

```text
locate -> fix
```

改成：

```text
locate -> suggest -> fix
```

也就是中间加入一个 **Suggester**，专门生成修复建议。

SGAgent 的核心架构包括：

- **Localizer**：定位可能出错的文件、函数、代码区域。
- **Suggester**：分析错误原因，提出修复方向和风险。
- **Fixer**：根据定位结果和修复建议生成补丁。
- **Knowledge Graph Toolkit**：用代码知识图谱辅助查找类、函数、变量、调用关系。
- **Testing and Voting**：生成多个候选补丁，通过测试和投票选择更好的补丁。

SGAgent 给我们的主要启发：

1. **不要直接从定位跳到修复**
   中间应该有“错误归因”和“修复建议”。

2. **Suggester 很关键**
   它把“哪里可能错”转化为“为什么错、怎么改、改了有什么风险”。

3. **多智能体应该有明确分工**
   每个 Agent 只负责一个清晰任务，而不是所有事情都让一个 Agent 做。

4. **仓库级修复需要结构化检索**
   后续可以加入函数级索引、调用关系、轻量知识图谱。

5. **多个候选补丁要通过测试筛选**
   不能只相信模型第一版 patch。

## 4. CodeR 的核心启发

CodeR 的重点是 **Multi-Agent + Task Graph**。

它认为代码修复不应该只依赖一个 Agent 临场自由规划，而应该像一个小型软件工程团队一样，由不同角色按照明确流程协作。

CodeR 的核心流程可以概括为：

```text
Manager -> Reproducer -> Fault Localizer -> Editor -> Verifier -> Submit
```

它的关键思想是 **Task Graph，任务图**。

任务图会提前规定：

- 哪个 Agent 负责哪个步骤。
- 当前步骤成功后去哪里。
- 当前步骤失败后去哪里。
- 什么时候继续修复。
- 什么时候提交或放弃。

CodeR 的核心 Agent 包括：

| Agent | 作用 |
|---|---|
| Manager | 选择任务计划，调度整体流程 |
| Reproducer | 根据 issue 生成复现测试，尝试复现 bug |
| Fault Localizer | 根据测试覆盖、检索结果定位可疑代码 |
| Editor | 修改代码，生成 patch |
| Verifier | 运行测试，判断 patch 是否有效 |

CodeR 给我们的主要启发：

1. **多智能体需要任务图约束**
   不能只让多个 Agent 自由聊天，否则容易循环、跑偏、信息丢失。

2. **Reproducer 很重要**
   真实 issue 往往没有现成失败测试。先生成复现测试，可以让修复更可验证。

3. **故障定位要结合测试覆盖和文本检索**
   CodeR 使用类似 `SBFL + BM25` 的思路，把运行时覆盖信息和 issue 文本相似度结合起来。

4. **Verifier 应该独立出来**
   修复 Agent 不应该自己判断 patch 好不好，应该交给测试和验证模块。

5. **任务流程应该配置化**
   同一个系统可以有不同 plan，例如：

```text
简单任务：Localize -> Edit -> Test
复杂任务：Reproduce -> FaultLocalize -> Suggest -> Edit -> Verify
失败重试：Verify failed -> Repair again
```

CodeR 对我们的意义：

> SWE-Agent 教我们设计工具接口，SGAgent 教我们加入修复建议，CodeR 教我们用任务图稳定地组织多智能体流程。

## 5. Agent-RLVR 与自进化训练路线

Agent-RLVR 给我们的核心启发是：

> 代码修复 Agent 不能只靠最终 pass/fail 奖励直接 RL，需要先用 SFT 冷启动，再用测试反馈和 guidance 缓解稀疏奖励。

下一阶段训练闭环固定为：

```text
任务运行
-> 轨迹记录
-> reward 打分
-> guidance 生成
-> SFT / DPO / OPD / RWR / RLVR 数据导出
-> memory 更新
-> 本地 smoke test / 服务器训练
```

五阶段训练路线：

```text
阶段 1：SFT 冷启动，学习工具格式和基础修复动作
阶段 2：DPO 偏好学习，偏向成功补丁和成功动作
阶段 3：OPD 自蒸馏，模仿高质量 on-policy 轨迹
阶段 4：RWR 轻量策略更新，用 reward 给动作样本加权
阶段 5：RLVR 服务器训练，用 visible / hidden tests 作为可验证奖励
```

本地版本只实现数据闭环，不训练大模型：

```text
codefixer_toy + local_rule_based
-> outputs/local_rl_smoke/
-> sft_train.jsonl / dpo_train.jsonl / opd_train.jsonl / rwr_train.jsonl / rlvr_rollouts.jsonl
```

服务器版本目标模型：

```text
Qwen2.5-Coder-7B-Instruct
```

训练原则：

- 本地不下载模型，不跑 PPO / GRPO。
- SWE-bench Lite / Verified 默认保留做评测。
- Guidance 初期由规则、测试日志、DiagnosisAgent、SuggesterAgent 生成。
- 后续服务器可以用强模型教师生成更高质量 guidance。

## 6. 我们下一阶段的系统架构

建议将 CodeFixer 升级为以下结构：

```text
ManagerAgent
  -> TaskGraph
  -> ReproducerAgent
  -> LocalizerAgent
  -> DiagnosisAgent
  -> SuggesterAgent
  -> RepairAgent
  -> CriticAgent
  -> VerifierAgent
  -> EvolutionAgent
```

各模块职责：

| 模块 | 作用 |
|---|---|
| ManagerAgent | 负责整体流程调度 |
| TaskGraph | 用配置文件规定 Agent 执行顺序和跳转逻辑 |
| ReproducerAgent | 根据 issue 生成或运行复现测试 |
| LocalizerAgent | 找到相关文件、函数、代码片段 |
| DiagnosisAgent | 判断 bug 类型和失败原因 |
| SuggesterAgent | 生成修复建议、影响范围和风险 |
| RepairAgent | 生成一个或多个候选补丁 |
| CriticAgent | 检查补丁是否危险、过拟合或过大 |
| VerifierAgent | 运行 visible / hidden / regression tests 并判断是否提交 |
| EvolutionAgent | 总结轨迹，生成 DPO / OPD / RLVR 训练数据 |

建议的默认任务图：

```text
start
 -> localize
 -> diagnose
 -> suggest
 -> repair
 -> verify
 -> if pass: submit
 -> if fail and budget remains: suggest / repair
 -> if fail and budget exhausted: final_report
```

进阶任务图：

```text
start
 -> reproduce
 -> fault_localize
 -> diagnose
 -> suggest
 -> repair
 -> critic
 -> verify
 -> submit_or_retry
```

## 7. 下一阶段优先实现内容

### 7.1 强化 ACI 工具接口

在现有工具基础上，逐步升级为 SWE-Agent 风格接口：

- `find_file`
- `search_file`
- `search_dir`
- `open_file`
- `goto_line`
- `scroll_window`
- `edit_lines`
- `run_tests`
- `run_hidden_tests`
- `get_diff`
- `revert_edit`
- `submit_patch`

重点改进：

- 支持按行查看代码。
- 支持按行编辑代码。
- 编辑后自动展示修改片段。
- 编辑后执行语法检查。
- 工具反馈统一为结构化 JSON。

### 7.2 新增 SuggesterAgent

新增一个中间 Agent，输出结构化修复建议：

```json
{
  "root_cause": "错误原因",
  "repair_plan": "修复计划",
  "target_files": ["相关文件"],
  "target_symbols": ["相关函数或类"],
  "risk_points": ["可能风险"],
  "expected_tests": ["应该通过的测试"]
}
```

它的作用是让 RepairAgent 不再盲目修复，而是基于明确计划生成 patch。

### 7.3 新增 TaskGraph 和 ReproducerAgent

新增任务图配置文件，例如：

```yaml
plan_default:
  entry: localize
  nodes:
    localize:
      agent: LocalizerAgent
      success: diagnose
      failure: diagnose
    diagnose:
      agent: DiagnosisAgent
      success: suggest
    suggest:
      agent: SuggesterAgent
      success: repair
    repair:
      agent: RepairAgent
      success: verify
    verify:
      agent: VerifierAgent
      success: submit
      failure: repair
```

ReproducerAgent 的初期目标不需要很复杂：

- 根据 issue 生成一个最小复现脚本。
- 尝试运行复现脚本。
- 如果复现成功，把失败日志交给 Localizer / Diagnosis。
- 如果复现失败，也继续使用已有 visible tests。

### 7.4 建立训练数据格式

为了训练 Qwen Coder 2.5 7B，我们需要保存以下数据：

1. **定位数据**

```text
issue + repo context -> target file / target function
```

2. **诊断数据**

```text
issue + failing tests + code -> bug type + root cause
```

3. **建议数据**

```text
issue + located code -> repair suggestion
```

4. **工具动作数据**

```text
observation + history -> next tool action
```

5. **补丁数据**

```text
issue + code + tests -> patch
```

6. **偏好数据**

```text
chosen successful patch > rejected failed patch
```

7. **任务图轨迹数据**

```text
task graph node + agent role + observation -> next node / action / result
```

### 7.5 训练 Qwen Coder 2.5 7B 的路线

不建议一开始直接做大规模 RL。

推荐路线：

```text
阶段 1：SFT 学会基础代码修复
阶段 2：SFT 学会 SWE-Agent 风格工具调用
阶段 3：DPO 学会偏好成功补丁
阶段 4：OPD / 自蒸馏 学会模仿高质量轨迹
阶段 5：RLVR 用测试结果做可验证奖励
```

优先数据来源：

- CodeFixer 自建 benchmark。
- HumanEvalFix。
- SWE-Agent trajectories。
- SWE-smith。
- SWE-Gym。
- BugsInPy / QuixBugs / Defects4J。

SWE-bench Lite / Verified 建议主要保留作评测，不要过早混入训练。

## 8. 下一阶段实验目标

我们需要比较三类系统：

| 系统 | 描述 |
|---|---|
| Baseline | 单 Agent，无建议、无记忆、弱反馈 |
| +ACI | 加入 SWE-Agent 风格工具接口和安全反馈 |
| +SGAgent | 加入 Localizer + Suggester + Repairer 多智能体流程 |
| +CodeR | 加入 TaskGraph、Reproducer、Verifier 和故障定位 |
| +Learning | 加入轨迹学习、DPO/OPD 数据和长期记忆 |

核心指标：

- Pass@1
- Pass@k
- Visible Test Pass Rate
- Hidden / Regression Test Pass Rate
- Average Tool Calls
- Average Test Runs
- Patch Size
- Unsafe Edit Rate
- Runtime Cost
- API / GPU Cost

推荐消融实验：

- 去掉 SuggesterAgent。
- 去掉 TaskGraph，改成自由多 Agent 调度。
- 去掉 ReproducerAgent。
- 去掉 Fault Localization。
- 去掉 ACI guardrail。
- 去掉测试反馈。
- 去掉失败轨迹记忆。
- 去掉 CriticAgent。
- 改变最大测试次数。
- 比较直接修复 vs 先诊断再修复。

## 9. 短期任务清单

下一阶段可以按这个顺序推进：

1. 新增 `SuggesterAgent`。
2. 新增 `TaskGraph` 配置和执行器。
3. 新增 `ReproducerAgent` 的最小版本。
4. 将工具接口升级为 SWE-Agent 风格 ACI。
5. 增加按行查看和按行编辑能力。
6. 增加编辑后的 lint / syntax guardrail。
7. 增加结构化 JSON 轨迹。
8. 增加 suggestion / reproduction / task graph 数据导出。
9. 增加 DPO / OPD / RLVR 数据导出字段。
10. 扩展 benchmark 到更接近真实仓库任务。
11. 接入 Qwen Coder 2.5 7B 作为可选 LLMPolicy。
12. 进行 Baseline / +ACI / +SGAgent / +CodeR / +Learning 对比实验。

## 10. 当前项目定位

CodeFixer 的下一阶段定位应为：

> 一个面向代码修复 Agent 的研究型平台，用 SWE-Agent 的 ACI 思想提升工具交互能力，用 SGAgent 的多智能体建议机制提升修复推理能力，用 CodeR 的任务图机制稳定组织多智能体流程，并最终为 Qwen Coder 2.5 7B 提供可训练、可评测、可自进化的数据闭环。
