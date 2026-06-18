#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001/v1}"
MODEL="${MODEL:-qwen3-coder-30b-a3b}"

echo "[check] Checking models endpoint: $API_BASE/models"
if ! curl -fsS "$API_BASE/models"; then
  echo
  echo "[check] vLLM server is not reachable." >&2
  echo "[check] Start it with: bash scripts/launch_vllm_qwen3.sh" >&2
  echo "[check] If port 8001 is occupied, inspect with: ps -ef | grep \"vllm serve\"" >&2
  exit 2
fi

echo
echo "[check] Testing chat completions for model: $MODEL"
curl -fsS "$API_BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Write a Python function add(a, b).\"}],\"temperature\":0,\"max_tokens\":128}"
echo
echo "[check] vLLM OpenAI-compatible endpoint looks usable."
