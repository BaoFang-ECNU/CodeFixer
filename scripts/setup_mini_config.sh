#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${MODEL_NAME:-hosted_vllm/qwen3-coder-30b-a3b}"
API_KEY_NAME="${API_KEY_NAME:-OPENAI_API_KEY}"
API_KEY_VALUE="${API_KEY_VALUE:-dummy}"

CONFIG_DIR="${MINI_SWE_AGENT_CONFIG_DIR:-/root/.config/mini-swe-agent}"
CONFIG_FILE="${CONFIG_DIR}/.env"

mkdir -p "${CONFIG_DIR}"
chmod 700 "${CONFIG_DIR}" || true

cat > "${CONFIG_FILE}" <<EOF
${API_KEY_NAME}='${API_KEY_VALUE}'
MSWEA_MODEL_NAME='${MODEL_NAME}'
MSWEA_MODEL_API_KEY_NAME='${API_KEY_NAME}'
EOF

chmod 600 "${CONFIG_FILE}" || true

echo "[mini-config] wrote ${CONFIG_FILE}"
cat "${CONFIG_FILE}"
echo
echo "[mini-config] Checking mini CLI. It should NOT show the quickstart setup prompt."
mini --help | head -20
