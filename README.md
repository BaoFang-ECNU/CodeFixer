# CodeFixer：面向代码修复 Agent 的自进化后训练

CodeFixer 是一个科研型代码修复 Agent 初期工程，主题是：

> 面向代码修复 Agent 的自进化后训练：从环境反馈到策略改进

项目当前实现了一个最小可运行闭环：从 toy bug-fix task 中读取 issue、代码文件和测试命令，让 Agent 观察环境、调用工具、编辑代码、运行测试、计算奖励、记录轨迹，并导出可用于后续 DPO / OPD / RLVR / self-evolution 的训练数据。

当前版本不追求一开始就跑完整 SWE-bench，而是优先保证工程闭环可运行、可复现、可扩展。

## 项目背景

代码修复 Agent 的核心问题是：给定一个包含 bug 的代码任务，Agent 如何通过多轮环境交互生成补丁，并从测试反馈中改进后续策略。

本项目参考了以下研究和工程路线：

- SWE-bench：真实 GitHub issue 级代码修复评测。
- SWE-agent：强调可控、可审计的 Agent 工具接口。
- AutoCodeRover：结构化检索与上下文定位。
- Agentless：定位、修复、验证、重排的强基线思路。
- RLVR / OPD / DPO：将可验证环境反馈转化为训练信号。
- Self-evolving Agent：从历史成功和失败轨迹中更新记忆与策略。

## 当前能力

当前版本已经支持：

- 从 `examples/toy_tasks/` 加载 toy 修复任务。
- 读取 `issue.md`、`buggy_code.py`、`test_buggy_code.py`。
- 初始化隔离的 `CodeRepairEnv` 工作目录。
- 使用工具执行 `inspect_file`、`search_code`、`edit_file`、`run_tests`、`get_diff`、`revert_last_edit`、`final_answer`。
- 每一步记录 trajectory。
- 运行测试并根据反馈计算 reward。
- 保存 patch diff、运行日志、评估结果。
- 生成 self-evolution 产物，包括 evolved policy、DPO preference data、OPD distillation data。
- 批量评估 toy tasks。
- 运行消融实验。

## 仓库结构

```text
CodeFixer/
  agent/                # Agent 主体、工具封装、多 Agent 外壳
  env/                  # 任务加载、代码环境、测试运行、patch 管理
  training/             # reward、trajectory、replay buffer、自进化、DPO/OPD 导出
  evaluation/           # 指标计算、批量评估、消融实验
  configs/              # 默认配置、奖励权重、toy task 列表
  docs/                 # 调研报告、算法设计、项目计划
  logs/                 # 轨迹日志、自进化摘要、临时工作目录
  examples/toy_tasks/   # toy code repair tasks
  scripts/              # 便捷运行脚本
  tests/                # smoke tests
  README.md
  requirements.txt
  Dockerfile
```

项目外还有一个独立算法文档：

```text
../tex/算法.tex
```

## 安装方式

推荐使用 Python 3.11。

### 使用 pip

```bash
pip install -r requirements.txt
```

### 使用 conda

```bash
conda create -n codefixer python=3.11 -y
conda activate codefixer
pip install -r requirements.txt
```

如果你在当前机器上使用已有的 `py311` 环境，可以运行：

```powershell
C:\Users\19310\anaconda3\envs\py311\python.exe -m pytest tests
```

## 快速运行

先进入项目根目录：

```powershell
cd C:\Users\19310\Desktop\创智大作业\CodeFixer
```

### 1. 运行单个 Agent 修复任务

```bash
python scripts/run_agent.py
```

该命令会加载第一个 toy task，执行以下流程：

1. 读取 issue 和代码。
2. 运行测试获得失败反馈。
3. 基于规则策略生成候选编辑。
4. 修改代码。
5. 再次运行测试。
6. 输出最终 patch 和结果。

### 2. 运行批量评估

```bash
python -m evaluation.evaluate --config configs/default.yaml
```

输出文件：

- `evaluation/results.json`
- `evaluation/summary.md`
- `logs/sample_trajectory.jsonl`
- `logs/replay_buffer.jsonl`
- `logs/evolution_summary.md`

### 3. 运行消融实验

```bash
python -m evaluation.ablation --config configs/default.yaml
```

输出文件：

- `evaluation/ablation_results.json`
- `evaluation/ablation_summary.md`

当前支持的消融包括：

- `baseline_rule_agent`
- `no_memory`
- `no_test_feedback`
- `no_self_evolution`
- `reward_no_patch_penalty`
- `max_steps_3`
- `max_steps_8`

### 4. 运行 smoke tests

```bash
python -m pytest tests
```

## 查看实验结果

常用结果文件如下：

- `evaluation/results.json`：批量评估的完整 JSON 结果。
- `evaluation/summary.md`：评估摘要表格。
- `evaluation/ablation_results.json`：消融实验完整结果。
- `evaluation/ablation_summary.md`：消融实验摘要。
- `logs/sample_trajectory.jsonl`：逐步轨迹日志。
- `training/evolved_policy.json`：自进化后的策略摘要。
- `training/dpo_data.jsonl`：DPO 偏好数据。
- `training/opd_distill.jsonl`：OPD 蒸馏数据。

其中 `logs/sample_trajectory.jsonl` 每一行记录一个 step，包括：

- `task_id`
- `step_id`
- `observation`
- `action`
- `action_args`
- `test_output`
- `reward`
- `done`
- `patch_diff`
- `timestamp`

## 如何添加新任务

在 `examples/toy_tasks/` 下创建新目录，例如：

```text
examples/toy_tasks/task_004/
  issue.md
  buggy_code.py
  test_buggy_code.py
```

然后在 `configs/tasks_toy.yaml` 中添加任务配置：

```json
{
  "task_id": "task_004",
  "issue": "examples/toy_tasks/task_004/issue.md",
  "source_files": ["examples/toy_tasks/task_004/buggy_code.py"],
  "test_files": ["examples/toy_tasks/task_004/test_buggy_code.py"],
  "test_command": "python -m pytest test_buggy_code.py"
}
```

注意：当前 `configs/*.yaml` 文件采用 JSON 兼容写法，因此即使没有安装 `PyYAML`，项目也可以用标准库 `json` 读取配置。

## 如何理解核心代码

建议按这个顺序阅读：

1. `env/task_loader.py`：任务如何从配置加载。
2. `env/code_env.py`：Agent 可交互环境和工具实现。
3. `env/test_runner.py`：测试命令如何执行。
4. `agent/coding_agent.py`：修复循环主逻辑。
5. `training/policy.py`：当前规则策略。
6. `training/reward.py`：奖励函数。
7. `training/trajectory.py`：轨迹结构。
8. `training/self_evolution.py`：自进化数据生成。
9. `evaluation/evaluate.py`：批量评估。
10. `evaluation/ablation.py`：消融实验。

## 自进化模块说明

当前自进化模块不是训练真实大模型，而是实现轻量闭环：

1. 从 evaluation 结果中收集 trajectory。
2. 区分成功和失败轨迹。
3. 总结失败原因。
4. 统计 action pattern。
5. 更新 memory / evolved policy。
6. 生成 DPO 和 OPD 数据格式。

生成文件：

```text
training/evolved_policy.json
training/dpo_data.jsonl
training/opd_distill.jsonl
logs/evolution_summary.md
```

后续可以把这些数据接入真实训练流程，例如 DPO preference tuning、OPD / on-policy distillation、reward-weighted regression、best-of-N + policy update、RLVR。

## 当前版本功能边界

当前版本已经能跑通最小闭环，但仍有明确限制：

- Agent 目前使用规则策略，不调用真实 LLM。
- 只支持简单 Python toy tasks。
- 没有真实 hidden tests。
- 没有接入 SWE-bench Lite 或 Defects4J。
- 没有真正训练模型参数。
- patch 生成依赖简单文本替换和模式匹配。
- 复杂仓库级定位、调用图、依赖安装、沙箱隔离还未实现。

这些限制是刻意保留的：项目第一阶段优先保证闭环清晰、可运行、可扩展。

## 后续路线图

下一阶段可以按以下方向扩展：

1. 接入 SWE-bench Lite task loader。
2. 接入 Defects4J Java 修复任务。
3. 增加 OpenAI API / 本地 LLM policy。
4. 实现 best-of-N 补丁生成和候选重排。
5. 引入 AST / 调用图 / 符号级代码检索。
6. 增加 hidden tests 和 regression tests。
7. 用 DPO / OPD / RLVR 对策略进行真实训练。
8. 扩展多 Agent 协作：ResearchAgent、AlgorithmAgent、CodingAgent、EvaluationAgent。
9. 增加 Web UI 或实验 dashboard。

## 常见问题

### 1. 没有安装 pytest 怎么办？

推荐安装：

```bash
pip install pytest
```

项目内部的 `TestRunner` 对 toy tasks 提供了一个极简 fallback，但正式实验仍建议安装 pytest。

### 2. 为什么配置文件后缀是 `.yaml`，内容却像 JSON？

这是为了兼容两种环境：

- 安装了 `PyYAML` 时，按 YAML 读取。
- 没有 `PyYAML` 时，按 JSON 读取。

JSON 本身是 YAML 的子集，因此这种写法仍然是合法 YAML。

### 3. 为什么 DPO 数据里有 no-op rejected？

如果所有 toy tasks 都被成功修复，就没有自然失败轨迹可配对。为了保证初期有可检查的 DPO 数据格式，系统会用成功编辑作为 `chosen`，用初始无补丁动作作为弱 `rejected`。

### 4. 临时修复代码在哪里？

每个任务会复制到 `logs/workspaces/` 下的隔离工作目录中运行。该目录是临时产物，不建议手动修改。

## 论文和报告材料

项目文档位于：

- `docs/research_report.md`
- `docs/algorithm_design.md`
- `docs/project_plan.md`

这些文件可作为课程报告、答辩材料和后续论文式扩展的初稿。

## 下一阶段更新内容

本版本已经在初始闭环基础上完成第二阶段增强：

- toy benchmark 从 3 个任务扩展到 8 个任务。
- 新增 bug 类型：字符串处理、空列表边界、简单动态规划、字典计数、异常处理。
- `RuleBasedPolicy` 增加更多模式修复能力。
- `LLMPolicy` 已实现可选接口，默认关闭；开启后只输出工具动作 JSON，不直接修改文件。
- 新增 `policy.type` 和 `llm.*` 配置项。
- 新增 `env/swebench_loader.py`，用于加载 SWE-bench Lite 风格任务元数据。
- 新增 `env/repo_workspace.py`，为真实仓库 clone、checkout、diff、apply patch 预留接口。
- 新增 GitHub Actions：push 或 pull request 时自动运行 smoke tests 和 toy evaluation。
- 新增 MIT License。
- 评估结果新增 `failure_reason`、`first_pass_step`、`patch_diff_lines`、`memory_enabled`、`test_feedback_enabled` 等字段。

### 可选 LLMPolicy 配置

默认配置仍使用规则策略：

```json
"policy": {
  "type": "rule_based"
}
```

如果后续要启用 LLMPolicy，可以改为：

```json
"policy": {
  "type": "llm"
}
```

并设置环境变量：

```bash
export OPENAI_API_KEY=your_api_key
```

在 Windows PowerShell 中：

```powershell
$env:OPENAI_API_KEY="your_api_key"
```

LLMPolicy 的输出必须是工具动作 JSON，例如：

```json
{
  "action": "edit_file",
  "args": {
    "path": "buggy_code.py",
    "old_text": "return name.lower()",
    "new_text": "return name.strip().lower()"
  },
  "rationale": "strip whitespace before lowercasing"
}
```

实际文件修改仍由 `CodeRepairEnv` 执行，因此轨迹和安全检查仍然可审计。

### GitHub 发布建议

当前本地仓库已经包含 `.github/workflows/ci.yml`。首次推送到 GitHub 前，建议执行：

```bash
git add .
git commit -m "Initial CodeFixer project"
git branch -M main
git remote add origin https://github.com/<username>/CodeFixer.git
git push -u origin main
```

将 `<username>` 替换为你的 GitHub 用户名。

## 第三阶段更新：自建基准、多系统评测与自进化

当前版本进一步加入了轻量自建基准、显式错误归因、多 Agent 协作和三版本系统对比。

### 构造轻量自建基准

```bash
python scripts/build_benchmark.py --config configs/benchmark_sources.yaml --max-tasks 20
```

该命令会生成：

- `configs/tasks_benchmark.yaml`
- `examples/benchmark_tasks/`

当前 benchmark 包含 10 个任务，覆盖 Python 和 JavaScript，并为每个任务保存：

- `issue.md`
- buggy source
- visible tests
- hidden/regression tests
- language、bug type、project source 等 metadata

### 三版本系统对比

```bash
python -m evaluation.compare_systems --config configs/tasks_benchmark.yaml
```

输出：

- `evaluation/system_comparison_results.json`
- `evaluation/system_comparison_summary.md`

三类系统版本：

- `baseline`：基础 Agent，无测试反馈反思、无自进化。
- `feedback`：加入测试反馈、诊断、候选修复和 critic 检查。
- `learning`：加入长期记忆、自进化数据导出、bug pattern 成功率统计。

### 单独运行某个系统版本

```bash
python -m evaluation.evaluate --config configs/tasks_benchmark.yaml --system-version baseline
python -m evaluation.evaluate --config configs/tasks_benchmark.yaml --system-version feedback
python -m evaluation.evaluate --config configs/tasks_benchmark.yaml --system-version learning
```

### 新增多 Agent 模块

- `DiagnosisAgent`：输出 `bug_type`、`confidence`、`evidence`、`recommended_actions`。
- `RepairAgent`：调用策略和工具生成补丁。
- `CriticAgent`：检查测试文件修改、硬编码、危险代码、补丁过大。
- `EvolutionAgent`：更新长期记忆，生成 DPO/OPD/RWR 训练数据。

### 新增指标

评估结果现在额外包含：

- `hidden_regression_test_pass_rate`
- `avg_test_runs`
- `patch_file_count`
- `api_cost_estimate`
- `runtime_cost_sec`
- 按 `system_version`、`bug_type`、`language`、`project_source` 分组的指标

### 新增训练与自进化产物

- `training/memory_patterns.json`
- `training/dpo_train.jsonl`
- `training/opd_train.jsonl`
- `training/rwr_train.jsonl`
- `logs/bug_taxonomy_summary.md`


