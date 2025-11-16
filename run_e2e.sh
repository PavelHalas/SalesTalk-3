#!/usr/bin/env bash
# Run Product Owner E2E suite with streaming progress output.
# Usage: ./run_e2e.sh [model]
# Example: ./run_e2e.sh llama3.2:latest
# Defaults to llama3.2:latest if not provided.

set -euo pipefail

MODEL="${1:-llama3.2:latest}"

export AI_PROVIDER=ollama
export OLLAMA_MODEL="$MODEL"
export USE_HIER_PASSES=true
export VERBOSE_E2E=true

cd /Users/pavel/Documents/Development/SalesTalk-3/backend
if [ -d .venv ]; then
	# shellcheck disable=SC1091
	source .venv/bin/activate || true
fi
echo "Running E2E with model=$MODEL (streaming enabled)" >&2
python -m pytest tests/e2e/test_product_owner_questions.py -q -s
