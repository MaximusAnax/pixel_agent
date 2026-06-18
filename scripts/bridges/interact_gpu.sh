#!/usr/bin/env bash
# Request an interactive GPU session on Bridges-2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../../config/bridges.env" 2>/dev/null || source "${SCRIPT_DIR}/../../config/bridges.env.example"

echo "Requesting GPU-shared session: charge=${BRIDGES_CHARGE_ID}"
interact -A "${BRIDGES_CHARGE_ID}" -p "${BRIDGES_PARTITION}" --gres=gpu:"${BRIDGES_GPUS}" -t 4:00:00
