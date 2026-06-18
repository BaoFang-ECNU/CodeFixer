#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/inspire/ssd/project/machine-behavior/czxs25150055/models/qwen3-coder-30b-a3b}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3-coder-30b-a3b}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-4}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
ENABLE_AUTO_TOOL_CHOICE="${ENABLE_AUTO_TOOL_CHOICE:-1}"
TOOL_CALL_PARSER="${TOOL_CALL_PARSER:-qwen3_xml}"

if [[ ! -d "$MODEL_PATH" ]]; then
  echo "[vllm] Model path does not exist: $MODEL_PATH" >&2
  echo "[vllm] Download or place the model manually first. This project never downloads large models automatically." >&2
  exit 2
fi

echo "[vllm] Starting $SERVED_MODEL_NAME from $MODEL_PATH on port $PORT"
echo "[vllm] First-run stability defaults: max_model_len=$MAX_MODEL_LEN, gpu_memory_utilization=$GPU_MEMORY_UTILIZATION"
if [[ "$ENABLE_AUTO_TOOL_CHOICE" == "1" ]]; then
  echo "[vllm] Tool calling enabled: --enable-auto-tool-choice --tool-call-parser $TOOL_CALL_PARSER"
fi

export CUDA_VISIBLE_DEVICES

if ! command -v vllm >/dev/null 2>&1; then
  echo "[vllm] 'vllm' command not found in PATH." >&2
  echo "[vllm] Activate the intended venv first:" >&2
  echo "  source /inspire/ssd/project/machine-behavior/czxs25150055/vllm-cu128-fast/bin/activate" >&2
  echo "[vllm] Then verify:" >&2
  echo "  which python" >&2
  echo "  which vllm" >&2
  echo "  python -c \"import vllm; print(vllm.__version__)\"" >&2
  exit 127
fi

ARGS=(
  "$MODEL_PATH"
  --served-model-name "$SERVED_MODEL_NAME"
  --host "$HOST"
  --port "$PORT"
  --trust-remote-code
  --tensor-parallel-size "$TENSOR_PARALLEL_SIZE"
  --dtype bfloat16
  --max-model-len "$MAX_MODEL_LEN"
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
)

if [[ "$ENABLE_AUTO_TOOL_CHOICE" == "1" ]]; then
  ARGS+=(--enable-auto-tool-choice --tool-call-parser "$TOOL_CALL_PARSER")
fi

exec vllm serve "${ARGS[@]}"
