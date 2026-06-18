# Local Evaluation Without SWE-bench Containers

The experiment server currently lacks Docker, Singularity, Apptainer, and contree. Standard SWE-bench execution is blocked, so this project includes a no-Docker evaluator for course-scale code repair tasks.

This tool is not a replacement for official SWE-bench scoring. It is a reproducible fallback for the section 6.3 metrics and for comparing:

- `Baseline`: no training or self-evolution
- `+ Feedback`: test feedback, reflection, or candidate reranking
- `+ Learning/Evolution`: Agentic RL, OPD, self-distillation, or memory-based improvement

## Metrics

The evaluator reports the section 6.3 metrics:

- `pass_at_1`: first generated patch succeeds.
- `pass_at_k`: at least one candidate patch succeeds.
- `visible_test_pass_rate`: public/visible tests pass.
- `hidden_regression_test_pass_rate`: hidden or regression tests pass.
- `average_tool_calls`: average tool calls parsed from trajectory or metadata.
- `average_test_runs`: average test command invocations.
- `average_patch_lines`: changed `+`/`-` lines in the patch.
- `average_patch_files`: changed files in the patch.
- `unsafe_edit_rate`: heuristic rate for unsafe edits.
- `average_cost`: API/token/GPU-hour cost if recorded in metadata.
- `average_wall_time_sec`: elapsed time if recorded, otherwise evaluator runtime.

Candidate-level output also includes:

- `test_deletion`
- `hardcoded_answer_risk`
- `irrelevant_file_edits`

## Manifest Format

See `configs/local_eval_example.yaml`.

Each task needs:

- `id`
- `repo_path`
- `issue`
- `relevant_files`
- `visible_test_command`
- `hidden_test_command`
- `hidden_test_patch` if hidden tests should be applied only during evaluation
- `timeout_sec`

Each system points to an attempts directory:

```yaml
systems:
  - name: baseline
    attempts_dir: outputs/local_runs/baseline
```

## Attempt Format

For each system/task/candidate:

```text
outputs/local_runs/<system>/<task_id>/candidate_0/
  patch.diff
  trajectory.json      # optional
  metadata.json        # optional
```

`metadata.json` can include:

```json
{
  "tool_calls": 12,
  "test_runs": 3,
  "cost": 0.0,
  "wall_time_sec": 91.2
}
```

## Run

```bash
python scripts/evaluate_local.py \
  --manifest configs/local_eval_example.yaml \
  --output-dir outputs/local_eval
```

Outputs:

```text
outputs/local_eval/candidate_metrics.csv
outputs/local_eval/system_metrics.csv
outputs/local_eval/system_metrics.md
```

## Suggested Course Workflow

Create 20-50 lightweight Python or JavaScript repair tasks from open-source repositories or small self-built repos. Keep hidden tests outside the agent prompt. For each task, save the agent patch and trajectory, then run this evaluator for Baseline, +Feedback, and +Learning/Evolution.

Use official SWE-bench later if a container runtime becomes available.

## Convert SWE-bench Lite To Local Task Skeletons

You can use SWE-bench records as the source of local tasks, but this is not official SWE-bench scoring. The conversion keeps the issue and base repo visible while storing `test_patch` separately as a hidden evaluation patch.

Inspect/export records first:

```bash
python scripts/inspect_swebench_dataset.py --split test --limit 5
```

Create task skeletons without cloning repos:

```bash
python scripts/prepare_swebench_local_tasks.py --split test --start 0 --limit 5
```

If the server has GitHub access, clone repos and checkout `base_commit`:

```bash
python scripts/prepare_swebench_local_tasks.py --split test --start 0 --limit 5 --clone
```

This writes:

```text
examples/local_tasks/swebench_lite/<instance_id>/
  repo/
  issue.md
  hidden_test.patch
  reference.patch
  record.json

configs/local_eval_swebench_lite.yaml
```

Then put baseline attempts here:

```text
outputs/local_runs/baseline/<instance_id>/candidate_0/patch.diff
outputs/local_runs/baseline/<instance_id>/candidate_0/trajectory.json
outputs/local_runs/baseline/<instance_id>/candidate_0/metadata.json
```

Evaluate:

```bash
python scripts/evaluate_local.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --output-dir outputs/local_eval_swebench_lite
```

Important caveats:

- The evaluator applies `hidden_test.patch` only after applying the agent patch, so hidden tests are not exposed through the task repo.
- Dependency setup is still repo-specific. Some SWE-bench repos may require extra installation commands that are normally handled by official containers.
- If a repo cannot run locally, either add setup commands manually or choose lighter tasks.
- Report this as a local SWE-bench-derived benchmark, not official SWE-bench Lite resolved rate.

## Run The Local Baseline End-To-End

After generating and cloning tasks, make sure vLLM is already serving `qwen3-coder-30b-a3b` and `mini` is available in the active environment:

```bash
bash scripts/check_vllm_server.sh
mini --help
```

Run one task first:

```bash
python scripts/run_local_task.py <instance_id> --system smoke --step-limit 20 --max-tokens 1024 --timeout-sec 600
```

Run the first 50 tasks:

```bash
python scripts/run_local_batch.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --start 0 \
  --limit 50 \
  --step-limit 80 \
  --max-tokens 1024 \
  --continue-on-error
```

Each attempt is saved as:

```text
outputs/local_runs/baseline/<instance_id>/candidate_0/
  prompt.txt
  mini_stdout.log
  trajectory.json
  patch.diff
  metadata.json
```

Then evaluate:

```bash
python scripts/evaluate_local.py \
  --manifest configs/local_eval_swebench_lite.yaml \
  --output-dir outputs/local_eval_swebench_lite
```

## Inspect SWE-bench Records Without Containers

You can inspect issues, repos, base commits, and reference patches without Docker:

```bash
python scripts/inspect_swebench_dataset.py --split test --limit 5
python scripts/inspect_swebench_dataset.py --split test --limit 20 --output outputs/swebench_lite_sample.json
```

This is useful for selecting tasks or designing local toy equivalents. It does not run repository tests and should not be reported as official SWE-bench execution.
