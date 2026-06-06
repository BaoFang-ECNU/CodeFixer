# Ablation Summary

- baseline_rule_agent: pass_at_1=1.0
- no_process_reward: pass_at_1=1.0
- no_teacher_correction: pass_at_1=1.0
- no_failure_memory: pass_at_1=1.0
- test_budget_1: pass_at_1=0.0
- test_budget_3: pass_at_1=1.0
- test_budget_8: pass_at_1=1.0
- localization_keyword_vs_diagnosis: pass_at_1=1.0
- direct_repair_vs_diagnose_then_repair: pass_at_1=1.0

# Ablation Rows

## Metrics
- pass_at_1: 0
- pass_at_k: 0
- visible_test_pass_rate: 0
- hidden_regression_test_pass_rate: 0
- avg_reward: 0
- avg_steps: 0
- avg_tool_calls: 0
- avg_test_runs: 0
- avg_runtime_sec: 0
- avg_patch_size: 0
- avg_patch_diff_lines: 0
- patch_file_count: 0
- unsafe_edit_rate: 0
- timeout_rate: 0
- api_cost_estimate: 0
- runtime_cost_sec: 0
- cost_estimate: 0

## Tasks
| task_id | version | bug_type | lang | visible | hidden | failure_reason | reward | tools | tests | patch_lines |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| baseline_rule_agent |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| no_process_reward |  |  |  | True |  | aggregate | 0.9525 | 4.0 | 0 | 2.375 |
| no_teacher_correction |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| no_failure_memory |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| test_budget_1 |  |  |  | False |  | aggregate | -0.1800 | 2.0 | 0 | 0.0 |
| test_budget_3 |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| test_budget_8 |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| localization_keyword_vs_diagnosis |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
| direct_repair_vs_diagnose_then_repair |  |  |  | True |  | aggregate | 0.9325 | 4.0 | 0 | 2.375 |
