#!/usr/bin/env bash
set -euo pipefail

echo "[setup] Installing lightweight baseline dependencies into the active Python environment."
echo "[setup] This script intentionally does not install or upgrade vLLM, torch, cuda, or nvidia packages."

python -m pip install -U pip
python -m pip install -U mini-swe-agent swebench datasets pandas pyyaml rich litellm pytest

echo "[setup] Done. Validate mini-SWE-agent CLI flags before launching a run:"
echo "  mini-extra swebench --help"
echo "  mini-extra swebench-single --help"
echo "  mini --help"
