# Evaluation Summary

## Metrics
- pass_at_1: 1.0
- pass_at_k: 1.0
- visible_test_pass_rate: 1.0
- hidden_regression_test_pass_rate: 1.0
- avg_reward: 0.94
- avg_steps: 2.0
- avg_tool_calls: 4.0
- avg_test_runs: 3.0
- avg_runtime_sec: 5.5671
- avg_patch_size: 2.0
- avg_patch_diff_lines: 2.0
- patch_file_count: 1.0
- unsafe_edit_rate: 0.0
- timeout_rate: 0.0
- api_cost_estimate: 0.012
- runtime_cost_sec: 16.7012
- cost_estimate: 0.012

## Tasks
| task_id | version | bug_type | lang | visible | hidden | failure_reason | reward | tools | tests | patch_lines |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| bench_py_001 | learning | off_by_one | python | True | True | passed | 0.9400 | 4 | 3 | 2 |
| bench_py_002 | learning | division_by_zero | python | True | True | passed | 0.9400 | 4 | 3 | 2 |
| bench_py_003 | learning | sorting_direction | python | True | True | passed | 0.9400 | 4 | 3 | 2 |
