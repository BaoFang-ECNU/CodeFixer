# Ablation: Candidate Reranker

## Candidate-0 Only
| system | num_tasks | num_candidates | pass_at_1 | pass_at_k | visible_test_pass_rate | fix_test_pass_rate | regression_test_pass_rate | hidden_regression_test_pass_rate | average_tool_calls | average_test_runs | average_patch_lines | average_patch_files | unsafe_edit_rate | submission_compliance_rate | empty_patch_rate | artifact_exposure_rate | average_cost | average_wall_time_sec | total_wall_time_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feedback_v3_candidate0_only_django44 | 44 | 44 | 0.25 | 0.25 | NA | 0.3 | 0.7 | 0.275 | 95.5 | 3.6136 | 379.4545 | 1.4773 | 0.3409 | 0.2955 | 0.0909 | 0.0 | 0.0 | 52.7233 | 2319.8273 |


## Candidate Pool
| system | num_tasks | num_candidates | pass_at_1 | pass_at_k | visible_test_pass_rate | fix_test_pass_rate | regression_test_pass_rate | hidden_regression_test_pass_rate | average_tool_calls | average_test_runs | average_patch_lines | average_patch_files | unsafe_edit_rate | submission_compliance_rate | empty_patch_rate | artifact_exposure_rate | average_cost | average_wall_time_sec | total_wall_time_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feedback_v3_candidates_django44 | 44 | 88 | 0.25 | 0.2727 | NA | 0.2875 | 0.6582 | 0.2375 | 101.6932 | 2.75 | 303.4886 | 1.4318 | 0.2727 | 0.3636 | 0.0909 | 0.0 | 0.0 | 52.5992 | 4628.7272 |


## Selected by Reranker
| system | num_tasks | num_candidates | pass_at_1 | pass_at_k | visible_test_pass_rate | fix_test_pass_rate | regression_test_pass_rate | hidden_regression_test_pass_rate | average_tool_calls | average_test_runs | average_patch_lines | average_patch_files | unsafe_edit_rate | submission_compliance_rate | empty_patch_rate | artifact_exposure_rate | average_cost | average_wall_time_sec | total_wall_time_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feedback_v3_django44 | 44 | 44 | 0.2727 | 0.2727 | NA | 0.3256 | 0.6667 | 0.2791 | 100.0682 | 3.0 | 230.5227 | 1.25 | 0.1591 | 0.5227 | 0.0227 | 0.0 | 0.0 | 50.5269 | 2223.1857 |


## V4 Global Candidate Pool
| system | num_tasks | num_candidates | pass_at_1 | pass_at_k | visible_test_pass_rate | fix_test_pass_rate | regression_test_pass_rate | hidden_regression_test_pass_rate | average_tool_calls | average_test_runs | average_patch_lines | average_patch_files | unsafe_edit_rate | submission_compliance_rate | empty_patch_rate | artifact_exposure_rate | average_cost | average_wall_time_sec | total_wall_time_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feedback_v4_bandit_candidates_django44 | 44 | 176 | 0.2045 | 0.3636 | NA | 0.3197 | 0.7014 | 0.2789 | 105.983 | 4.9034 | 585.8466 | 1.6477 | 0.2955 | 0.4091 | 0.1193 | 0.0 | 0.0 | 69.0666 | 12155.7219 |


## V4 Global Selected
| system | num_tasks | num_candidates | pass_at_1 | pass_at_k | visible_test_pass_rate | fix_test_pass_rate | regression_test_pass_rate | hidden_regression_test_pass_rate | average_tool_calls | average_test_runs | average_patch_lines | average_patch_files | unsafe_edit_rate | submission_compliance_rate | empty_patch_rate | artifact_exposure_rate | average_cost | average_wall_time_sec | total_wall_time_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| feedback_v4_bandit_django44 | 44 | 44 | 0.2727 | 0.2727 | NA | 0.3095 | 0.6585 | 0.2857 | 98.8409 | 3.5227 | 178.2727 | 1.2273 | 0.1136 | 0.75 | 0.0 | 0.0 | 0.0 | 56.3037 | 2477.363 |



Interpretation:
- Candidate-0 Only removes reranking and always keeps the first generated candidate.
- Candidate Pool pass@k is the oracle upper bound over generated candidates.
- V4 Global Bandit increases candidate-pool pass@k, while selected pass@1 shows the remaining selection gap.
- This supports the conclusion that reranking/reward calibration is a key remaining bottleneck.

