# CodeFixer：面向代码修复 Agent 的自进化后训练

**重要服务器环境要求：如果要运行 Defects4J 真实 checkout / compile / test，请优先使用 Linux 服务器，并提前安装 Java 11、Git、Subversion、Perl、cpanm 和 Defects4J；Windows 本地主要用于 toy / benchmark smoke test 与配置生成验证。**

CodeFixer 是一个科研型代码修复 Agent 工程。它把“带 bug 的代码任务”建模为一个可交互环境：Agent 读取 issue、检查文件、编辑代码、运行测试、根据反馈计算 reward、记录 trajectory，并导出 SFT / DPO / OPD / RWR / RLVR 等后续训练数据。

当前版本优先保证最小闭环可运行，不在本地下载大模型，也不在本地训练 Qwen。服务器训练阶段可以复用本仓库导出的轨迹和训练数据。

## 服务器部署与评测快速说明书

### 1. 推荐服务器环境

本地 smoke test 和 toy benchmark 只需要 CPU；如果后续要训练 Qwen2.5-Coder-7B，建议使用 GPU 服务器。

基础环境：

```bash
conda create -n codefixer python=3.11 -y
conda activate codefixer
pip install -r requirements.txt
```

当前最小依赖：

```text
pytest>=8.0
PyYAML>=6.0
```

如果要在服务器上接入 7B 模型训练，建议额外准备：

```text
CUDA / GPU 驱动
PyTorch
transformers
datasets
accelerate
peft
trl 或 verl
wandb 或 tensorboard
```

这些训练依赖当前没有写入 `requirements.txt`，因为本仓库默认不强制下载大模型。建议后续单独创建 `requirements-train.txt` 或服务器环境脚本。

### 2. 需要下载什么 skill / 工具

运行 CodeFixer 本身不需要下载额外 Codex skill。只需要：

- `git`：拉取代码。
- `python=3.11`：运行 Agent、评测和消融。
- `pytest`：执行 toy task 测试。
- `PyYAML`：读取配置。
- 可选 `node` / `npm`：如果运行 JavaScript benchmark tasks。

如果你在 Codex Desktop 中继续写论文、处理 PDF 或生成文档，可以使用 Codex 自带的 `pdf`、`documents`、`spreadsheets` 等 skill；但这些不是代码库运行依赖。

### 3. 快速验证代码是否能跑

进入仓库根目录：

```bash
cd CodeFixer
```

本地最小测试：

```bash
python scripts/run_local_mini_test.py
```

自进化数据导出 smoke test：

```bash
python scripts/run_local_rl_smoke.py
```

单元测试：

```bash
python -m pytest tests -q
```

如果 Windows 上 `python` 指向 Microsoft Store shim，可以直接使用 conda 环境解释器，例如：

```powershell
C:\Users\19310\anaconda3\envs\py311\python.exe -m pytest tests -q
```

### 4. 评测、三版本对比与消融命令

单系统评测：

```bash
python -m evaluation.evaluate --config configs/default.yaml --max-tasks 2
```

三版本对比：

```bash
python -m evaluation.compare_systems --config configs/default.yaml --max-tasks 2
```

消融实验：

```bash
python -m evaluation.ablation --config configs/default.yaml --max-tasks 2
```

三个系统版本含义：

- `baseline`：基础规则 Agent，不使用自进化导出。
- `feedback`：加入测试反馈、多 Agent 诊断/修复/critic 流程。
- `learning`：加入长期记忆、自进化、SFT/DPO/OPD/RWR/RLVR 数据导出。

### 5. 哪些文件负责评测和消融

核心入口：

```text
evaluation/evaluate.py          # 单系统批量评测
evaluation/compare_systems.py   # baseline / feedback / learning 三版本对比
evaluation/ablation.py          # 消融实验
evaluation/metrics.py           # 指标计算
```

常用配置：

```text
configs/default.yaml            # 默认评测配置
configs/ablations.yaml          # 消融实验配置
configs/tasks_toy.yaml          # toy tasks 列表
configs/tasks_benchmark.yaml    # 自建 benchmark tasks 列表
configs/training_pipeline.yaml  # 自进化/训练数据导出配置
configs/models.yaml             # 模型注册表
configs/datasets.yaml           # 数据集注册表
```

### 6. 运行结果在哪里看

默认评测结果写入：

```text
outputs/evaluation/results.json
outputs/evaluation/summary.md
outputs/evaluation/trajectory.jsonl
outputs/evaluation/replay_buffer.jsonl
outputs/evaluation/training/
```

三版本对比结果：

```text
outputs/evaluation/system_comparison_results.json
outputs/evaluation/system_comparison_summary.md
```

消融结果：

```text
outputs/evaluation/ablations/ablation_results.json
outputs/evaluation/ablations/ablation_summary.md
```

本地 mini 测试结果：

```text
outputs/local_mini_test/results.json
outputs/local_mini_test/summary.md
outputs/local_mini_test/trajectory.jsonl
```

RL smoke test 结果：

```text
outputs/local_rl_smoke/results.json
outputs/local_rl_smoke/summary.md
outputs/local_rl_smoke/training/sft_train.jsonl
outputs/local_rl_smoke/training/dpo_train.jsonl
outputs/local_rl_smoke/training/opd_train.jsonl
outputs/local_rl_smoke/training/rwr_train.jsonl
outputs/local_rl_smoke/training/rlvr_rollouts.jsonl
outputs/local_rl_smoke/training/guidance_train.jsonl
```

`outputs/` 已加入 `.gitignore`，适合保存本地或服务器实验产物，不会污染仓库提交。

### 7. 指标含义速查

- `pass_at_1`：每个任务第一次尝试成功的比例。
- `pass_at_k`：每个任务最多尝试 k 次，只要一次成功就算成功。
- `visible_test_pass_rate`：公开测试通过率。
- `hidden_regression_test_pass_rate`：隐藏/回归测试通过率。
- `avg_tool_calls`：平均工具调用次数。
- `avg_test_runs`：平均测试运行次数。
- `avg_patch_diff_lines`：平均补丁行数。
- `unsafe_edit_rate`：危险修改比例，例如修改测试、越权编辑等。
- `SFT / DPO / OPD / RWR / RLVR`：导出的训练数据数量。
- `guidance_coverage`：轨迹步骤中带有 guidance 的比例。

### 8. 服务器训练推荐流程

第一步，在本地或服务器先跑 smoke test：

```bash
python scripts/run_local_rl_smoke.py
```

第二步，导出训练数据：

```bash
python scripts/export_training_data.py --config configs/training_pipeline.yaml
```

第三步，检查服务器训练模板：

```bash
python scripts/server_train_qwen.py --config configs/training_pipeline.yaml
```

当前 `server_train_qwen.py` 只输出训练配置和命令模板，不会真正启动大模型训练。真正训练 Qwen2.5-Coder-7B 时，需要在服务器上接入具体训练框架，例如 `transformers + peft + trl` 或 `verl`。

## 项目结构

```text
CodeFixer/
  agent/                # Agent 主体、多 Agent 协作、诊断、修复、critic
  env/                  # 任务加载、代码环境、测试运行、patch 管理
  training/             # reward、trajectory、replay、自进化、DPO/OPD/RLVR 导出
  evaluation/           # 指标、评测、三版本对比、消融实验
  configs/              # 任务、奖励、模型、数据集、训练配置
  docs/                 # 调研报告、算法设计、训练路线文档
  examples/             # toy tasks 和 benchmark tasks
  scripts/              # 常用运行脚本
  tests/                # 单元测试和 smoke tests
  outputs/              # 本地/服务器实验输出，默认不提交 Git
```

## 当前能力

- 加载 toy code repair tasks。
- 支持 Python 和轻量 JavaScript benchmark task 格式。
- 支持工具调用：`inspect_file`、`search_code`、`edit_file`、`run_tests`、`get_diff`、`revert_last_edit`、`final_answer`。
- 支持 trajectory 记录。
- 支持 reward 计算。
- 支持 baseline / feedback / learning 三版本对比。
- 支持消融实验。
- 支持导出 SFT、DPO、OPD、RWR、RLVR、guidance 数据。
- 预留 Qwen2.5-Coder-7B 服务器训练接口。

## 如何添加新任务

在 `examples/toy_tasks/` 或 `examples/benchmark_tasks/` 下创建任务目录，例如：

```text
examples/toy_tasks/task_009/
  issue.md
  buggy_code.py
  test_buggy_code.py
```

然后在 `configs/tasks_toy.yaml` 中加入任务配置：

```json
{
  "task_id": "task_009",
  "issue": "examples/toy_tasks/task_009/issue.md",
  "source_files": ["examples/toy_tasks/task_009/buggy_code.py"],
  "test_files": ["examples/toy_tasks/task_009/test_buggy_code.py"],
  "test_command": "python -m pytest test_buggy_code.py",
  "language": "python",
  "bug_type": "boundary_condition",
  "difficulty": "easy"
}
```

## 当前限制

- 当前默认策略仍以规则 Agent 为主，不直接调用真实 LLM 修复代码。
- 本地测试只验证小规模 toy / benchmark 任务，不代表 SWE-bench 成绩。
- hidden tests 目前主要是轻量构造的 regression proxy。
- Qwen2.5-Coder-7B 训练尚未在本仓库内真正启动，只提供数据导出和服务器训练模板。
- 当前 pass@1 较高主要因为 toy tasks 简单，后续需要增加更难任务才能形成有效科研对比。

## 后续路线

1. 扩展自建 benchmark 到更多 Python / JavaScript 项目。
2. 接入 SWE-bench Lite / Verified。
3. 接入真实 LLMPolicy，让模型只输出工具动作 JSON。
4. 在服务器上训练 Qwen2.5-Coder-7B。
5. 对比 SFT、DPO、OPD、RWR、RLVR 对代码修复能力的影响。
6. 增强多 Agent 协作：DiagnosisAgent、RepairAgent、CriticAgent、EvolutionAgent。
7. 增加更严格的 unsafe edit 检查和 hidden/regression tests。
