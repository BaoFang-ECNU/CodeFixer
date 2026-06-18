#!/usr/bin/env bash
set -euo pipefail

INDEX="${1:-}"
if [[ -z "$INDEX" ]]; then
  echo "Usage: bash scripts/run_single.sh <test_split_index>" >&2
  exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/configs/qwen3_vllm_mini_swe.yaml}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/runs/qwen3_lite_single_$INDEX}"
OUT_FILE="${OUT_FILE:-$OUT_DIR/qwen3_lite_single_${INDEX}.traj.json}"
MODEL="${MODEL:-hosted_vllm/qwen3-coder-30b-a3b}"
ENVIRONMENT_CLASS="${ENVIRONMENT_CLASS:-docker}"

export LITELLM_MODEL_REGISTRY_PATH="$PROJECT_ROOT/configs/litellm_registry.json"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"
export MSWEA_COST_TRACKING="${MSWEA_COST_TRACKING:-ignore_errors}"
export PAGER=cat
export GIT_PAGER=cat
export TQDM_DISABLE=1

mkdir -p "$OUT_DIR"

if ! command -v mini-extra >/dev/null 2>&1; then
  echo "[run_single] mini-extra not found. Install dependencies with: bash scripts/setup_env.sh" >&2
  exit 127
fi

if [[ "$ENVIRONMENT_CLASS" == "docker" ]] && ! command -v docker >/dev/null 2>&1; then
  echo "[run_single] Docker is required for the default SWE-bench environment, but 'docker' was not found in PATH." >&2
  echo "[run_single] Ask the server admin to enable Docker, load the Docker environment, or try another mini-SWE-agent environment class." >&2
  echo "[run_single] If Singularity/contree is available, try for example:" >&2
  echo "  ENVIRONMENT_CLASS=singularity bash scripts/run_single.sh $INDEX" >&2
  echo "  ENVIRONMENT_CLASS=contree bash scripts/run_single.sh $INDEX" >&2
  exit 127
fi

echo "[run_single] Output trajectory: $OUT_FILE"
echo "[run_single] Environment class: $ENVIRONMENT_CLASS"
echo "[run_single] If this command fails due to CLI changes, run:"
echo "  mini-extra swebench-single --help"
echo "  mini-extra swebench --help"
echo "  mini --help"

set +e
mini-extra swebench-single \
  --yolo \
  --cost-limit 0 \
  --subset lite \
  --split test \
  --instance "$INDEX" \
  --model "$MODEL" \
  --config swebench.yaml \
  --config "$CONFIG_PATH" \
  --environment-class "$ENVIRONMENT_CLASS" \
  --output "$OUT_FILE"
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
  echo "[run_single] mini-extra swebench-single failed, likely because CLI flags changed or the environment is not ready." >&2
  echo "[run_single] Current help follows for quick adjustment:" >&2
  mini-extra swebench-single --help || true
  exit "$status"
fi
