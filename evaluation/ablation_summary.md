# Ablation Summary


Task scope: first 3 tasks.

| ablation | pass@1 | pass@k | visible pass | hidden/regression pass | avg reward | avg tools | avg tests | patch lines | unsafe rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_rule_agent | 0.0 | 0.0 | 0.0 | 0.3333 | -0.18 | 3.0 | 1.0 | 0.0 | 0.0 |
| no_process_reward | 1.0 | 1.0 | 1.0 | 1.0 | 0.96 | 4.0 | 3.0 | 2.0 | 0.0 |
| no_teacher_correction | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |
| no_failure_memory | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |
| test_budget_1 | 0.0 | 0.0 | 0.0 | 0.3333 | -0.18 | 2.0 | 2.0 | 0.0 | 0.0 |
| test_budget_3 | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |
| test_budget_8 | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |
| localization_keyword_vs_diagnosis | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |
| direct_repair_vs_diagnose_then_repair | 1.0 | 1.0 | 1.0 | 1.0 | 0.94 | 4.0 | 3.0 | 2.0 | 0.0 |

## Aggregate Rows

| ablation | success | reward | tools | tests | patch_lines | hidden/regression |
|---|---:|---:|---:|---:|---:|---:|
| baseline_rule_agent | False | -0.1800 | 3.0 | 1.0 | 0.0 | 0.3333 |
| no_process_reward | True | 0.9600 | 4.0 | 3.0 | 2.0 | 1.0 |
| no_teacher_correction | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
| no_failure_memory | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
| test_budget_1 | False | -0.1800 | 2.0 | 2.0 | 0.0 | 0.3333 |
| test_budget_3 | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
| test_budget_8 | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
| localization_keyword_vs_diagnosis | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
| direct_repair_vs_diagnose_then_repair | True | 0.9400 | 4.0 | 3.0 | 2.0 | 1.0 |
