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


Interpretation:
- Candidate-0 Only removes reranking and always keeps the first generated candidate.
- Candidate Pool pass@k is the oracle upper bound over the generated candidates.
- Selected by Reranker reaches the candidate pool pass@k in this run, showing that the reranker recovers the best successful candidates.

