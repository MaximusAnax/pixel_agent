#!/usr/bin/env bash
# Build a taxonomy-discovery HTML review packet on Babel from cached HF zips.
#
# Uses the shared mattlab repo + shared outputs.
#
# Usage (from errorAnalysis/ on laptop):
#   source config/babel.env
#   git push && scripts/babel/sync_shared_repo.sh pull
#   PACKET_ID=pilot_taxonomy_paired_20260703 \
#   A3B_RUN=20260626_172919_a3b_pilot_full_v4 \
#   B7_RUN=20260626_172922_7b_pilot_full_v4 \
#   scripts/babel/build_review_packet.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@login.babel.cs.cmu.edu}"
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_REPO:=${BABEL_GROUP_ROOT}/pixelAgent}"
: "${BABEL_SHARED_ERROR_ANALYSIS:=${BABEL_SHARED_REPO}/errorAnalysis}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"
: "${BABEL_PACKET_STAGING:=${BABEL_GROUP_ROOT}/review_packets}"
: "${BABEL_REVIEW_STAGING:=${BABEL_HOME_DIR}/cua-failure-analysis/data/review_packets}"
: "${BABEL_USER_DATA:=/data/user_data/${BABEL_USER}}"
: "${BABEL_DATA_ROOT:=${BABEL_USER_DATA}/cua_failure_analysis}"
: "${BABEL_RAW_ROOT:=${BABEL_DATA_ROOT}/hf_raw}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=02:00:00}"
: "${BABEL_STAGE_MEM:=32G}"

A3B_RUN="${A3B_RUN:-20260626_172919_a3b_pilot_full_v4}"
B7_RUN="${B7_RUN:-20260626_172922_7b_pilot_full_v4}"
PACKET_ID="${PACKET_ID:-pilot_taxonomy_$(date +%Y%m%d)}"
SELECTION_MODE="${SELECTION_MODE:-paired-pilot}"

ZIP_A3B="${ZIP_A3B:-${BABEL_RAW_ROOT}/opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip}"
ZIP_7B="${ZIP_7B:-${BABEL_RAW_ROOT}/opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps.zip}"

A3B_RUN_DIR="${BABEL_SHARED_OUTPUT_ROOT}/${A3B_RUN}"
B7_RUN_DIR="${BABEL_SHARED_OUTPUT_ROOT}/${B7_RUN}"
PACKET_DIR="${BABEL_PACKET_STAGING}/${PACKET_ID}"
STAGING_DIR="${BABEL_REVIEW_STAGING}/${PACKET_ID}"

echo "Updating shared repo on Babel..."
"${SCRIPT_DIR}/sync_shared_repo.sh" pull

ssh "${BABEL_LOGIN}" "mkdir -p '${STAGING_DIR}'"

REMOTE_CMD=$(cat <<EOF
set -euo pipefail
cd '${BABEL_SHARED_ERROR_ANALYSIS}'
export PYTHONPATH='${BABEL_SHARED_ERROR_ANALYSIS}/src'
PY='${BABEL_SHARED_VENV}/bin/python'
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

rsync -a --delete '${PACKET_DIR}/' '${STAGING_DIR}/'

printf '%s\n' \\
  '# Active trace review state' \\
  "packet_id: ${PACKET_ID}" \\
  "built: $(date -u +%Y-%m-%d)" \\
  'annotators: abdoul, raghav' \\
  'tasks: 30 pilot (60 traces)' \\
  > '${BABEL_GROUP_ROOT}/REVIEW_STATE.md'

echo "Built review packet: ${PACKET_DIR}"
echo "Home mirror: ${STAGING_DIR}"
ls -la '${STAGING_DIR}/index.html'
EOF
)

echo "Building review packet ${PACKET_ID} on Babel (srun ${BABEL_STAGE_PARTITION})..."
ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=2 --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
  bash --noprofile --norc -s" <<< "${REMOTE_CMD}"

echo "Done. Sync with: scripts/babel/sync_review_packet.sh ${PACKET_ID}"
