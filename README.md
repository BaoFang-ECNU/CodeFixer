# codefixer-baseline

V0 baseline for the course project: vanilla mini-SWE-agent + local Qwen3-Coder-30B-A3B-Instruct + SWE-bench Lite.

This repository intentionally does not implement structured feedback, a learned selector, training, fine-tuning, or any paid API integration. The priority is a reproducible baseline with saved trajectories, predictions, evaluation outputs, and summary tables.

## Server Environment

Use the existing venv on the experiment server:

```bash
source /inspire/ssd/project/machine-behavior/czxs25150055/vllm-cu128-fast/bin/activate
```

Important paths and names:

- Project path on server: `/inspire/hdd/project/machine-behavior/czxs25150055/codefixer-baseline`
- Old CodeFixer project: `/inspire/hdd/project/machine-behavior/czxs25150055/CodeFixer-main`
- Local Qwen3 model path: `/inspire/ssd/project/machine-behavior/czxs25150055/models/qwen3-coder-30b-a3b`
- Qwen3 API base: `http://127.0.0.1:8001/v1`
- Served model name: `qwen3-coder-30b-a3b`

The model must already exist locally. This project only checks the model path and never downloads large models automatically.

## Install Lightweight Dependencies

```bash
bash scripts/setup_env.sh
```

The script installs mini-SWE-agent, SWE-bench, datasets, pandas, PyYAML, Rich, LiteLLM, and pytest. It intentionally does not install or upgrade vLLM, torch, CUDA, or NVIDIA packages. vLLM is assumed to already exist in the provided venv.

Before running experiments, check the installed CLI:

```bash
mini-extra swebench --help
mini-extra swebench-single --help
mini --help
```

Initialize mini-SWE-agent's global config after a fresh environment restart:

```bash
bash scripts/setup_mini_config.sh
```

This writes `/root/.config/mini-swe-agent/.env` with:

- `MSWEA_MODEL_NAME=hosted_vllm/qwen3-coder-30b-a3b`
- `MSWEA_MODEL_API_KEY_NAME=OPENAI_API_KEY`
- `OPENAI_API_KEY=dummy`

`mini --help` must not show the quickstart prompt. If it asks for "Enter your
default model" or "Enter your API key name", run `bash scripts/setup_mini_config.sh`
again before batch experiments.

mini-SWE-agent CLI flags and YAML schema may change across versions. If they differ, edit `scripts/run_single.sh`, `scripts/run_slice.sh`, and `configs/qwen3_vllm_mini_swe.yaml`.

## Launch Qwen3 With vLLM

Foreground:

```bash
bash scripts/launch_vllm_qwen3.sh
```

Optional nohup logging:

```bash
nohup bash scripts/launch_vllm_qwen3.sh > outputs/vllm_qwen3.log 2>&1 &
```

Default launch settings:

- `CUDA_VISIBLE_DEVICES=0,1,2,3`
- Tensor parallel size: `4`
- dtype: `bfloat16`
- Port: `8001`
- Initial max model length: `16384`
- Max sequences: `1`
- GPU memory utilization: `0.90`
- Tool calling: `--enable-auto-tool-choice --tool-call-parser qwen3_xml`

If stable, try `MAX_MODEL_LEN=32768`. If OOM happens, try `MAX_MODEL_LEN=8192` or `GPU_MEMORY_UTILIZATION=0.85`.

Check the server:

```bash
bash scripts/check_vllm_server.sh
```

The served model name, LiteLLM registry name, and mini-SWE-agent model name must stay aligned:

- `qwen3-coder-30b-a3b`
- `configs/litellm_registry.json`
- `hosted_vllm/qwen3-coder-30b-a3b`

## Run One Instance

```bash
bash scripts/run_single.sh 0
```

Default output:

```text
outputs/runs/qwen3_lite_single_0/
```

## Run A Small Slice

```bash
bash scripts/run_slice.sh 0 5
bash scripts/run_slice.sh 0 20
```

Default output for `0 5`:

```text
outputs/runs/qwen3_lite_test_0_5/
```

Workers default to `1`. Increase only after the single-worker path is stable.

## Evaluate

```bash
bash scripts/run_eval.sh outputs/runs/qwen3_lite_test_0_5/preds.json qwen3_lite_0_5
```

If `preds.json` is missing, the script tries the matching `preds.jsonl`. To inspect actual outputs:

```bash
find outputs/runs -type f
```

Before official submission, audit the prediction file for the patch output
protocol:

```bash
python scripts/audit_predictions.py outputs/runs/qwen3_lite_test_0_5/preds.json \
  --output-csv outputs/qwen3_lite_test_0_5_patch_protocol.csv
```

Malformed natural-language outputs are counted as baseline failures. For a
strict submission file that replaces non-compliant patches with empty patches:

```bash
python scripts/audit_predictions.py outputs/runs/qwen3_lite_test_0_5/preds.json \
  --write-strict-preds outputs/runs/qwen3_lite_test_0_5/preds.strict.json
```

To run an LLM-based patch sanitization pass over an existing local run directory
without regenerating trajectories:

```bash
python scripts/llm_sanitize_patches.py \
  --runs-dir outputs/local_runs/baseline_raw_49152_llm_sanitized \
  --api-base http://127.0.0.1:8001/v1 \
  --model qwen3-coder-30b-a3b \
  --max-tokens 4096 \
  --report-csv outputs/summary/llm_sanitize_report.csv
```

This is a submission-formatting pass, not a feedback or repair pass: it should
remove prose, malformed patch text, temporary reproduction files, and test
edits while preserving only source-code changes already present in the
candidate patch.

## Inspect And Summarize Outputs

```bash
python scripts/inspect_outputs.py
python scripts/collect_summary.py
```

Summary files:

```text
outputs/summary/baseline_summary.csv
outputs/summary/baseline_summary.md
```

## Output Directories

- `outputs/runs`: mini-SWE-agent run outputs, trajectories, predictions, and logs
- `outputs/summary`: collected CSV and Markdown summaries
- `outputs/vllm_qwen3.log`: optional vLLM nohup log

## Baseline Protocol

Fixed V0 settings:

- Agent: vanilla mini-SWE-agent
- Model: Qwen3-Coder-30B-A3B-Instruct
- Served model name: `qwen3-coder-30b-a3b`
- Inference: local vLLM, TP=4, bf16
- Port: 8001
- Max model length: 16384 initially
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
- Patch output protocol audit before official submission

For mini-SWE-agent/SWE-ReX runs, include the baseline patch protocol config
after the built-in SWE-bench configs:

```bash
mini-extra swebench \
  -c /usr/local/lib/python3.12/dist-packages/minisweagent/config/benchmarks/swebench.yaml \
  -c /usr/local/lib/python3.12/dist-packages/minisweagent/config/benchmarks/swebench_modal.yaml \
  -c configs/qwen3_vllm_mini_swe.yaml \
  -c configs/patch_protocol_mini_swe.yaml \
  -c model.model_class=litellm \
  -c model.model_name=hosted_vllm/qwen3-coder-30b-a3b \
  -c model.model_kwargs.api_base=http://127.0.0.1:8001/v1 \
  -c model.model_kwargs.max_tokens=4096 \
  --subset lite \
  --split test \
  --slice 6:50 \
  --workers 1 \
  --environment-class swerex_modal \
  -o runs/qwen3coder30b_lite_modal_django44_protocol
```

See [docs/baseline_protocol.md](docs/baseline_protocol.md) for the experiment protocol.

## Local Evaluation Fallback

If SWE-bench containers are unavailable on the server, use the local no-Docker evaluator for course-scale tasks:

```bash
python scripts/evaluate_local.py \
  --manifest configs/local_eval_example.yaml \
  --output-dir outputs/local_eval
```

It reports the section 6.3 metrics: `Pass@1`, `Pass@k`, visible test pass rate, hidden/regression test pass rate, average tool calls, average test runs, patch size, unsafe edit rate, and cost. See [docs/local_evaluation.md](docs/local_evaluation.md).

You can still inspect SWE-bench Lite records without Docker:

```bash
python scripts/inspect_swebench_dataset.py --split test --limit 5
python scripts/inspect_swebench_dataset.py --split test --limit 20 --output outputs/swebench_lite_sample.json
```

To create local SWE-bench-derived task skeletons:

```bash
python scripts/prepare_swebench_local_tasks.py --split test --start 0 --limit 5 --clone
python scripts/run_local_batch.py --manifest configs/local_eval_swebench_lite.yaml --start 0 --limit 5 --continue-on-error
python scripts/evaluate_local.py --manifest configs/local_eval_swebench_lite.yaml --output-dir outputs/local_eval_swebench_lite
```

This is a fallback benchmark, not official SWE-bench scoring.

## Local +Feedback Variant

The `+feedback` variant keeps the baseline runner intact and adds a separate
multi-candidate controller:

- candidate generation with mini-SWE-agent
- patch compliance checks
- visible-test execution when a visible command is available
- compact failure summaries for the next candidate
- candidate reranking into a selected output directory

It does not use hidden tests for feedback.

Run one task:

```bash
python scripts/run_feedback_task.py django__django-10914 \
  --candidate-system feedback_candidates_django44 \
  --selected-system feedback_django44 \
  --attempts 2 \
  --step-limit 1000 \
  --max-tokens 4096 \
  --timeout-sec 1800
```

Run the Django slice:

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

Candidate attempts are saved under `outputs/local_runs/feedback_candidates_django44`.
The reranked best patch for each task is saved under
`outputs/local_runs/feedback_django44`, which can be evaluated with the same
local evaluator as the baseline.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md).

Common checks:

- vLLM OOM: lower `MAX_MODEL_LEN` to `8192` or `GPU_MEMORY_UTILIZATION` to `0.85`.
- vLLM startup says free memory is too low: run `nvidia-smi`; another process is already occupying at least one selected GPU.
- Port 8001 occupied: run `ps -ef | grep "vllm serve"`, stop the stale process if appropriate, or change `PORT`.
- LiteLLM model/provider issue: ensure `hosted_vllm/qwen3-coder-30b-a3b`, registry, and served model name match.
- Docker unavailable: first verify `mini-extra --help` paths, then fix Docker before full SWE-bench evaluation.
- If Docker is unavailable but Singularity or contree is installed, try `ENVIRONMENT_CLASS=singularity bash scripts/run_single.sh 0` or `ENVIRONMENT_CLASS=contree bash scripts/run_single.sh 0`.
- mini-extra CLI changed: run the help commands and adjust the two run scripts.
- No paid API: `OPENAI_API_KEY=dummy` is enough for local vLLM.
- Idle stop policy: if the system stops low-GPU jobs after about 3 hours, keep vLLM receiving occasional requests during long idle periods or stop/restart intentionally.

## Local Tests

Tests do not require GPU, vLLM, SWE-bench downloads, mini-SWE-agent execution, or Docker.

```bash
python -m pytest tests -q
```
