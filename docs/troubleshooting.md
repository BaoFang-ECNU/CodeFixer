# Troubleshooting

## vLLM OOM

Start with `MAX_MODEL_LEN=16384`. If the server runs out of memory, try:

```bash
MAX_MODEL_LEN=8192 bash scripts/launch_vllm_qwen3.sh
GPU_MEMORY_UTILIZATION=0.85 bash scripts/launch_vllm_qwen3.sh
```

Only try `MAX_MODEL_LEN=32768` after the 16384 setting is stable.

If startup fails with a message like:

```text
Free memory on device (1.42/47.38 GiB) on startup is less than desired GPU memory utilization
```

then another process is already using that GPU. Lowering `GPU_MEMORY_UTILIZATION` only helps when the card is mostly free. First inspect GPU ownership:

```bash
nvidia-smi
ps -ef | grep "vllm serve"
```

Stop stale jobs if they are yours, or choose a free set of GPUs:

```bash
CUDA_VISIBLE_DEVICES=4,5,6,7 bash scripts/launch_vllm_qwen3.sh
```

For the expected 4 * 4090 setup, each selected GPU should have roughly 40 GiB or more free before starting the 30B model with tensor parallel size 4.

## Port 8001 Is Occupied

Qwen2.5-Coder-7B may already be using 8000, so Qwen3 defaults to 8001. If 8001 is occupied:

```bash
ps -ef | grep "vllm serve"
```

Stop the stale process if appropriate, or launch with another port:

```bash
PORT=8002 bash scripts/launch_vllm_qwen3.sh
API_BASE=http://127.0.0.1:8002/v1 bash scripts/check_vllm_server.sh
```

Keep the served model name, LiteLLM model name, and mini-SWE-agent model name aligned.

## LiteLLM Cannot Find Provider Or Model

Check all three names:

- vLLM `--served-model-name qwen3-coder-30b-a3b`
- `configs/litellm_registry.json`
- `configs/qwen3_vllm_mini_swe.yaml`

The mini-SWE-agent model should be `hosted_vllm/qwen3-coder-30b-a3b`.

## mini-SWE-agent Enters Quickstart During Batch Runs

If logs contain:

```text
To get started, we need to set up your global config file.
Enter your default model
Enter your API key name
Aborted.
```

then mini-SWE-agent's global config is incomplete. Batch runs are
non-interactive, so the quickstart prompt aborts the task.

Run:

```bash
bash scripts/setup_mini_config.sh
```

The config file should contain:

```text
OPENAI_API_KEY='dummy'
MSWEA_MODEL_NAME='hosted_vllm/qwen3-coder-30b-a3b'
MSWEA_MODEL_API_KEY_NAME='OPENAI_API_KEY'
```

Check:

```bash
mini --help | head -20
```

It may print `Loading global config`, but it must not ask for the default model
or API key name. `scripts/run_local_task.py` also injects these values into the
mini subprocess environment as a backup.

## vLLM Rejects tool_choice auto

mini-SWE-agent uses tool calls. If vLLM returns:

```text
"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

restart vLLM with tool calling enabled:

```bash
bash scripts/launch_vllm_qwen3.sh
```

The launch script defaults to:

```bash
--enable-auto-tool-choice --tool-call-parser qwen3_xml
```

If the installed vLLM does not recognize `qwen3_xml`, inspect available parsers:

```bash
vllm serve --help | grep -A3 -B3 tool-call-parser
```

## Context Window Exceeded

If vLLM returns an error like:

```text
'max_tokens' is too large: 8192. This model's maximum context length is 16384 tokens and your request has 8858 input tokens
```

the agent prompt plus trajectory is too long for the requested completion budget. Lower the completion budget:

```bash
python scripts/run_local_task.py astropy__astropy-12907 \
  --system smoke \
  --step-limit 20 \
  --max-tokens 1024 \
  --timeout-sec 600
```

For difficult large repos, `--max-tokens 1024` or `--max-tokens 512` is reasonable for smoke tests. Also reduce command output by using `grep` or `sed -n` instead of `cat` on large files.

## Docker Is Unavailable

SWE-bench evaluation normally expects Docker. First validate local CLI availability:

```bash
mini-extra swebench --help
mini-extra swebench-single --help
mini --help
which docker
docker info
```

Then run a tiny slice after Docker is available. If the server does not provide Docker but has a mini-SWE-agent-supported alternative, try:

```bash
which singularity
which contree
ENVIRONMENT_CLASS=singularity bash scripts/run_single.sh 0
ENVIRONMENT_CLASS=contree bash scripts/run_single.sh 0
```

The default scripts use `ENVIRONMENT_CLASS=docker` because SWE-bench's reference path is Docker-based. If neither Docker nor a supported alternative is available, SWE-bench Lite cannot run on that machine until the container runtime is enabled.

## mini-extra CLI Flags Changed

mini-SWE-agent CLI flags may change. The project intentionally keeps CLI calls in:

- `scripts/run_single.sh`
- `scripts/run_slice.sh`

Run the help commands and edit those scripts if the current mini-SWE-agent version uses different flag names.

## preds.json Does Not Exist

Inspect actual files:

```bash
find outputs/runs -type f
```

Some versions may write `preds.jsonl` or place predictions under a nested run directory. `scripts/run_eval.sh` checks the `.json` and `.jsonl` variants automatically when possible.

## No Paid API Is Used

`OPENAI_API_KEY` is set to `dummy`. The local vLLM OpenAI-compatible endpoint does not need a real OpenAI key. Do not place real API keys in this repository.

## Automatic Idle Stop Policy

The server may stop jobs if GPU utilization stays at or below 15% for about 3 hours. During long idle periods such as manual model placement or debugging, keep vLLM receiving occasional requests or stop and restart it intentionally.
