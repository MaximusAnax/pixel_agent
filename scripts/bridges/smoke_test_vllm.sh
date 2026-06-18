#!/usr/bin/env bash
# Curl vLLM /v1/models from inside the cluster (run on compute node or login with node hostname).
set -euo pipefail

HOST="${1:-localhost}"
PORT="${2:-8000}"
BASE="http://${HOST}:${PORT}/v1"

echo "Testing ${BASE}/models ..."
curl -sf "${BASE}/models" | python3 -m json.tool

echo ""
echo "Smoke test OK."
