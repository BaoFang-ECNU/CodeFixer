# Algorithm Design

## POMDP Model

- Observation: issue text, source file snapshot, test files, last test output,
  current diff, tool-call count, unsafe-edit count, and remaining budget.
- Hidden state: true repository state, hidden tests, dependency health, and
  whether the patch generalizes.
- Actions: `inspect_file`, `search_code`, `edit_file`, `run_tests`, `get_diff`,
  `revert_last_edit`, `final_answer`.
- Transition: read-only tools reveal context; edits mutate the workspace; tests
  reveal partial correctness; memory updates after rollouts.
- Reward: visible pass reward plus improvement reward minus patch-size, tool,
  unsafe-edit, timeout, and no-progress penalties.
- Termination: tests pass, max steps are exhausted, timeout occurs, or the agent
  produces a final answer.

## Policy

The current `RuleBasedPolicy` follows a localization-edit-validate pattern:
run tests first, infer common bug patterns from issue and failure output, apply a
candidate text edit, and immediately validate it. It covers off-by-one,
division by zero, sorting direction, string normalization, empty-boundary,
simple DP transition, dictionary counting, and exception-handling bugs. The
optional `LLMPolicy` builds a tool-action prompt and requires the model to
return JSON rather than directly editing files. `TrainablePolicy` remains the
future RL/OPD/DPO policy interface.

## Self-Evolution

The trainer reads replayed trajectories, counts successful action patterns,
summarizes failures, writes an evolved memory artifact, and exports:

- DPO JSONL: `prompt`, `chosen`, `rejected`, `chosen_reward`,
  `rejected_reward`.
- OPD JSONL: `observation`, `teacher_action`, `reward`, `rationale`.
- Best-of-N ranking: candidate patches are sorted by reward, safety, patch size,
  and tool-call cost.
