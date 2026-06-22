#!/usr/bin/env bash
# Pull compact Babel analysis artifacts back to the local workspace.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@babel.lti.cs.cmu.edu}"
: "${BABEL_OUTPUT_ROOT:=/data/user_data/${BABEL_USER}/cua_failure_analysis/outputs}"

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: scripts/babel/sync_outputs.sh <run_id>"
  exit 2
fi

LOCAL_DIR="${REPO_ROOT}/data/babel_outputs/${RUN_ID}"
mkdir -p "${LOCAL_DIR}"

rsync -az \
  --include '*/' \
  --include '*.json' \
  --include '*.jsonl' \
  --include '*.csv' \
  --include '*.md' \
  --exclude '*' \
  "${BABEL_LOGIN}:${BABEL_OUTPUT_ROOT}/${RUN_ID}/" "${LOCAL_DIR}/"

echo "Synced ${RUN_ID} to ${LOCAL_DIR}"
