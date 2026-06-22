# V0 Baseline Protocol: mini-SWE-agent + Qwen3-Coder-30B-A3B on SWE-bench Lite

## Research Question

Without structured feedback, learned feedback selection, training, or fine-tuning, what SWE-bench Lite repair capability can local Qwen3-Coder-30B-A3B-Instruct reach when driven by vanilla mini-SWE-agent?

## Why This Is The Baseline

All later variants should be compared against this run. The goal is to avoid attributing the base model's existing coding and repair ability to later feedback strategies.

Fixed baseline settings:

- Agent: vanilla mini-SWE-agent
- Model: Qwen3-Coder-30B-A3B-Instruct
- Served model name: qwen3-coder-30b-a3b
- Inference: local vLLM OpenAI-compatible server, TP=4, bf16
- Port: 8001
- Initial max model length: 16384
- Temperature: 0
- SWE-bench subset: Lite
- Split: test
- Workers: 1
- Step limit: 80
- No structured feedback
- No selector
- No training
- No fine-tuning
- No paid API

## Patch Output Protocol

The baseline is intentionally free of learning and task feedback, but it should
still obey the SWE-bench submission contract. A submitted `model_patch` must be
a machine-applicable unified diff, not a natural-language summary.

Required patch-level protocol:

- The patch is empty only when the agent genuinely produced no candidate fix.
- Non-empty patches must contain valid headers such as
  `diff --git a/path b/path`.
- Patches must not edit tests or benchmark artifacts.
- The raw model output and the protocol-audited submission are reported
  separately when they differ.
- The task prompt instructs the model to finish by creating `/tmp/final.patch`
  with `git diff --binary`, checking it with `git apply --check`, and submitting
  exactly `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat /tmp/final.patch`.

This protocol does not use hidden tests and is not a feedback or learning
module. It is the task output contract. For mini-SWE-agent/SWE-ReX runs, include:

```bash
-c configs/patch_protocol_mini_swe.yaml
```

After generation, audit the output format before official submission:

```bash
python scripts/audit_predictions.py runs/<run_name>/preds.json \
  --output-csv outputs/<run_name>_patch_protocol.csv
```

For a strict submission file that replaces non-compliant patches with empty
patches:

```bash
python scripts/audit_predictions.py runs/<run_name>/preds.json \
  --write-strict-preds runs/<run_name>/preds.strict.json
```

Malformed patches are counted as a baseline failure mode, not repaired by hand.

## Later Versions

- V1: structured-feedback mini-SWE-agent
- V2: learned-selector mini-SWE-agent
- V3: optional self-evolution or preference data export

### V1 +Feedback Variant

V1 keeps V0 as the control condition and adds a local feedback controller around
mini-SWE-agent. It generates multiple candidates and feeds only allowed local
signals into later attempts:

- patch compliance checks: empty patch, malformed diff, test edits, artifact edits
- clean patch application to the base repository
- visible test command result, if the task metadata provides one
- compact stdout/stderr failure summaries

V1 does not use hidden tests, reference patches, official verdicts, or
PASS_TO_PASS/FAIL_TO_PASS outcomes as feedback. Those remain evaluation signals.

The controller saves all attempts under a candidate system and copies the
highest-ranked attempt into a selected system:

```bash
python scripts/run_feedback_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --candidate-system feedback_candidates_django44 \
  --selected-system feedback_django44 \
  --start 6 \
  --limit 44 \
  --attempts 2 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800 \
  --continue-on-error
```

The selected system can be evaluated with the same local evaluator as V0, which
keeps the comparison controlled.

### V3 Learning/Evolution Variant

V3 adds a lightweight evolution memory on top of V2. The memory is built from
previous feedback reports only:

- candidate patch-compliance checks
- patch-apply checks
- visible-test feedback, if available
- failure summaries and selected-candidate metadata

V3 does not use reference patches, official SWE-bench verdicts, hidden test
contents, or benchmark artifact contents as feedback. Hidden/regression tests
remain evaluation-only signals.

Build an evolution memory from a completed feedback run:

```bash
python scripts/build_evolution_memory.py \
  --feedback-dir outputs/feedback \
  --output outputs/memory/feedback_v2_evolution_memory.md
```

Run the next feedback/evolution pass with that memory:

```bash
python scripts/run_feedback_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --candidate-system feedback_v3_candidates_django44 \
  --selected-system feedback_v3_django44 \
  --feedback-root outputs/feedback_v3_django44_reports \
  --memory-file outputs/memory/feedback_v2_evolution_memory.md \
  --start 6 \
  --limit 44 \
  --attempts 2 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800 \
  --continue-on-error
```

The memory is stored in each task's feedback report and copied into each
candidate prompt as process guidance. It is an evolution mechanism for process
discipline, not a task-answer cache.

### V4 Bandit Prompt Controller

V4 keeps the V3 memory and reranker, then adds a lightweight prompt-policy
controller. Each prompt policy is treated as a bandit arm, and the controller
uses Thompson sampling to choose which policy to use for later candidates in a
task. The first candidate is always the V3 control policy for comparability.

The available prompt arms are:

- `v3_control`: the standard V3 feedback/evolution prompt.
- `localization_first`: identify the real source owner before editing.
- `failing_test_first`: map the visible failure signal to a minimal source fix.
- `minimal_patch`: optimize for a small source-only patch.
- `regression_conservative`: preserve public behavior and avoid overfitting.
- `traceback_api_contract`: repair Django API/contract boundaries.

Bandit rewards are computed from local, allowed signals only: patch application,
visible test result, patch compliance, patch size, unsafe edits, workdir drift,
and artifact exposure. Hidden tests, reference patches, official verdicts, and
benchmark artifacts are never used as training feedback.

The controller supports three Thompson-sampling variants:

- `bandit`: a global bandit shared across all failure modes.
- `contextual_bandit`: a contextual bandit whose state is keyed by the previous
  candidate's failure type, such as `patch_not_apply`, `assertion_error`,
  `syntax_error`, `import_error`, `timeout`, and `unsafe_or_noncompliant`.
- `hierarchical_bandit`: a HierTS-lite controller that keeps the same contextual
  state but smooths sparse context-local posteriors with the global arm
  posterior. For context `c` and arm `a`, it samples from
  `Beta(alpha_local(c,a) + lambda_c * alpha_global(a),
  beta_local(c,a) + lambda_c * beta_global(a))`, where
  `lambda_c = tau / (tau + n_c)`. This lets early or rare failure contexts borrow
  global prompt-policy evidence while gradually trusting local context data.

Example global-bandit command:

```bash
python scripts/run_feedback_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --candidate-system feedback_v4_bandit_candidates_django44 \
  --selected-system feedback_v4_bandit_django44 \
  --feedback-root outputs/feedback_v4_bandit_django44_reports \
  --memory-file outputs/memory/feedback_v2_evolution_memory.clean.md \
  --prompt-controller bandit \
  --bandit-state outputs/feedback_v4_bandit_django44_reports/bandit_state.json \
  --bandit-seed 17 \
  --start 6 \
  --limit 44 \
  --attempts 4 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800 \
  --continue-on-error
```

Example contextual-bandit command:

```bash
python scripts/run_feedback_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --candidate-system feedback_v4_contextual_candidates_django44 \
  --selected-system feedback_v4_contextual_django44 \
  --feedback-root outputs/feedback_v4_contextual_django44_reports \
  --memory-file outputs/memory/feedback_v2_evolution_memory.clean.md \
  --prompt-controller contextual_bandit \
  --bandit-state outputs/feedback_v4_contextual_django44_reports/bandit_state.json \
  --bandit-seed 29 \
  --start 6 \
  --limit 44 \
  --attempts 4 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800 \
  --continue-on-error
```

Example HierTS-lite command:

```bash
python scripts/run_feedback_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --candidate-system feedback_v4_hier_candidates_django44 \
  --selected-system feedback_v4_hier_django44 \
  --feedback-root outputs/feedback_v4_hier_django44_reports \
  --memory-file outputs/memory/feedback_v2_evolution_memory.clean.md \
  --prompt-controller hierarchical_bandit \
  --bandit-state outputs/feedback_v4_hier_django44_reports/bandit_state.json \
  --bandit-seed 43 \
  --hier-tau 3.0 \
  --start 6 \
  --limit 44 \
  --attempts 4 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800 \
  --continue-on-error
```

The selected system can be evaluated like any other local run. For true
`pass@k`, evaluate the candidate system as well as the selected system.

When running multiple experiments on a shared filesystem, always give each
experiment a distinct `--candidate-system`, `--selected-system`, and
`--feedback-root`. Otherwise parallel jobs can overwrite each other's
`outputs/feedback/<task_id>/feedback_report.json` files.

## Metrics

- Resolved rate
- Repair@k if later experiments generate multiple candidates
- Average step count
- Average wall time
- Failure type distribution
- Trajectory count
- Evaluation success and failure counts
- Empty patch rate
- Malformed patch rate
- Valid unified diff rate
- Submission compliance rate

## Ablation Slots

These are not implemented in V0, but the baseline keeps room for later comparison:

- Remove structured feedback
- Remove learned selector
- Remove execution verification
- Compare feedback formats
- Compare step limits
- Compare temperatures
