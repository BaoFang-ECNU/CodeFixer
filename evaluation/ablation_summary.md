# Ablation Summary

- baseline_rule_agent: pass_at_1=1.0
- no_memory: pass_at_1=1.0
- no_test_feedback: pass_at_1=0.0
- no_self_evolution: pass_at_1=1.0
- reward_no_patch_penalty: pass_at_1=1.0
- max_steps_3: pass_at_1=1.0
- max_steps_8: pass_at_1=1.0

# Ablation Rows

## Metrics
- pass_at_1: 0
- pass_at_k: 0
- visible_test_pass_rate: 0
- avg_reward: 0
- avg_steps: 0
- avg_tool_calls: 0
- avg_runtime_sec: 0
- avg_patch_size: 0
- avg_patch_diff_lines: 0
- unsafe_edit_rate: 0
- timeout_rate: 0
- cost_estimate: 0

## Tasks
| task_id | success | first_pass_step | failure_reason | reward | steps | tool_calls | patch_lines |
|---|---:|---:|---|---:|---:|---:|---:|
| baseline_rule_agent | True |  | aggregate | 0.9325 | 2.0 | 4.0 | 2.375 |
| no_memory | True |  | aggregate | 0.9325 | 2.0 | 4.0 | 2.375 |
| no_test_feedback | False |  | aggregate | -0.6300 | 6.0 | 6.0 | 0.0 |
| no_self_evolution | True |  | aggregate | 0.9325 | 2.0 | 4.0 | 2.375 |
| reward_no_patch_penalty | True |  | aggregate | 0.9800 | 2.0 | 4.0 | 2.375 |
| max_steps_3 | True |  | aggregate | 0.9325 | 2.0 | 4.0 | 2.375 |
| max_steps_8 | True |  | aggregate | 0.9325 | 2.0 | 4.0 | 2.375 |
