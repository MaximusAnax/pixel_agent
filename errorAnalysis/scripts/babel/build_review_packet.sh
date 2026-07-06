#!/usr/bin/env bash
# Build a taxonomy-discovery HTML review packet on Babel from cached HF zips.
#
# Usage (from errorAnalysis/ on laptop):
#   source config/babel.env
#   PACKET_ID=pilot_taxonomy_20260630 \
#   A3B_RUN=20260626_172919_a3b_pilot_full_v4 \
#   B7_RUN=20260626_172922_7b_pilot_full_v4 \
#   scripts/babel/build_review_packet.sh
#
# Then sync to laptop:
#   scripts/babel/sync_review_packet.sh pilot_taxonomy_20260630

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@login.babel.cs.cmu.edu}"
: "${BABEL_PROJECT_DIR:=/home/${BABEL_USER}/cua-failure-analysis}"
: "${BABEL_DATA_ROOT:=/data/user_data/${BABEL_USER}/cua_failure_analysis}"
: "${BABEL_RAW_ROOT:=${BABEL_DATA_ROOT}/hf_raw}"
: "${BABEL_OUTPUT_ROOT:=${BABEL_DATA_ROOT}/outputs}"
: "${BABEL_REVIEW_ROOT:=${BABEL_DATA_ROOT}/review_packets}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=01:00:00}"
: "${BABEL_STAGE_MEM:=16G}"

A3B_RUN="${A3B_RUN:-20260626_172919_a3b_pilot_full_v4}"
B7_RUN="${B7_RUN:-20260626_172922_7b_pilot_full_v4}"
PACKET_ID="${PACKET_ID:-pilot_taxonomy_$(date +%Y%m%d)}"
SELECTION_MODE="${SELECTION_MODE:-paired-pilot}"
: "${BABEL_STAGE_TIME:=02:00:00}"
: "${BABEL_STAGE_MEM:=32G}"

ZIP_A3B="${ZIP_A3B:-${BABEL_RAW_ROOT}/opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip}"
ZIP_7B="${ZIP_7B:-${BABEL_RAW_ROOT}/opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps.zip}"

A3B_RUN_DIR="${BABEL_OUTPUT_ROOT}/${A3B_RUN}"
B7_RUN_DIR="${BABEL_OUTPUT_ROOT}/${B7_RUN}"
PACKET_DIR="${BABEL_REVIEW_ROOT}/${PACKET_ID}"
STAGING_DIR="${BABEL_PROJECT_DIR}/data/review_packets/${PACKET_ID}"

echo "Syncing errorAnalysis to ${BABEL_LOGIN}:${BABEL_PROJECT_DIR}"
ssh "${BABEL_LOGIN}" "mkdir -p '${BABEL_PROJECT_DIR}' '${BABEL_PROJECT_DIR}/logs' '${STAGING_DIR}'"
rsync -az --delete \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'data/babel_outputs' \
  --exclude 'data/review_packets' \
  --exclude 'config/babel.env' \
  --exclude 'external' \
  --exclude 'logs' \
  "${REPO_ROOT}/" "${BABEL_LOGIN}:${BABEL_PROJECT_DIR}/"

REMOTE_CMD=$(cat <<EOF
set -euo pipefail
cd '${BABEL_PROJECT_DIR}'
export PYTHONPATH='${BABEL_PROJECT_DIR}/src'
PY='${BABEL_PROJECT_DIR}/.venv/bin/python'
if [[ ! -x "\${PY}" ]]; then PY=python3; fi

mkdir -p '${PACKET_DIR}' '${STAGING_DIR}'

"\${PY}" scripts/select_review_episodes.py \\
  --run-dirs '${A3B_RUN_DIR}' '${B7_RUN_DIR}' \\
  --mode '${SELECTION_MODE}' \\
  --packet-id '${PACKET_ID}' \\
  --output-dir '${PACKET_DIR}'

"\${PY}" scripts/build_trace_review_packet.py \\
  --manifest '${PACKET_DIR}/manifest.json' \\
  --zip-a3b '${ZIP_A3B}' \\
  --zip-7b '${ZIP_7B}' \\
  --output-dir '${PACKET_DIR}'

"\${PY}" scripts/export_discovery_worksheet.py \\
  --manifest '${PACKET_DIR}/packet_manifest.json' \\
  --output '${PACKET_DIR}/taxonomy_discovery_labels.csv'

# Stage compact + media to home for rsync (login node cannot read /data/user_data directly)
rsync -a --delete '${PACKET_DIR}/' '${STAGING_DIR}/'
echo "Staged review packet: ${STAGING_DIR}"
ls -la '${STAGING_DIR}/index.html'
EOF
)

echo "Building review packet ${PACKET_ID} on Babel (srun ${BABEL_STAGE_PARTITION})..."
ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=2 --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
  bash --noprofile --norc -s" <<< "${REMOTE_CMD}"

echo "Done. Sync with: scripts/babel/sync_review_packet.sh ${PACKET_ID}"
