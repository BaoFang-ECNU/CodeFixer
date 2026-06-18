#!/usr/bin/env bash
set -euo pipefail

PREDS_PATH="${1:-}"
RUN_ID="${2:-}"
if [[ -z "$PREDS_PATH" || -z "$RUN_ID" ]]; then
  echo "Usage: bash scripts/run_eval.sh <preds.json|preds.jsonl> <run_id>" >&2
  exit 2
fi

if [[ ! -f "$PREDS_PATH" ]]; then
  if [[ "$PREDS_PATH" == *.json && -f "${PREDS_PATH%.json}.jsonl" ]]; then
    PREDS_PATH="${PREDS_PATH%.json}.jsonl"
  elif [[ "$PREDS_PATH" == *.jsonl && -f "${PREDS_PATH%.jsonl}.json" ]]; then
    PREDS_PATH="${PREDS_PATH%.jsonl}.json"
  else
    echo "[eval] Predictions file not found: $PREDS_PATH" >&2
    echo "[eval] Inspect actual outputs with: find outputs/runs -type f" >&2
    exit 2
  fi
fi

python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite \
  --split test \
  --predictions_path "$PREDS_PATH" \
  --max_workers 1 \
  --run_id "$RUN_ID"
