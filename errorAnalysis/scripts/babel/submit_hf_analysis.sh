#!/usr/bin/env bash
# Submit a Phase 1 HF OSWorld failure-analysis job to Babel.
#
# Usage:
#   cp config/babel.env.example config/babel.env
#   source config/babel.env
#   scripts/babel/submit_hf_analysis.sh opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip

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
: "${BABEL_PARTITION:=cpu}"
: "${BABEL_TIME:=06:00:00}"
: "${BABEL_CPUS:=8}"
: "${BABEL_MEM:=64G}"
: "${BABEL_GPUS:=0}"
# Babel requires a GPU type in the gres request, e.g. gpu:L40S:1 (not gpu:1).
: "${BABEL_GPU_TYPE:=L40S}"
: "${OSWORLD_PACKAGE:=${1:-opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip}}"
: "${OSWORLD_MAX_EPISODES:=25}"
: "${OSWORLD_PHASE:=all}"
: "${OSWORLD_FAILED_ONLY:=0}"
: "${STAGE_NORMALIZED_TRACES:=0}"

if [[ $# -ge 1 ]]; then
  OSWORLD_PACKAGE="$1"
fi

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_${OSWORLD_PACKAGE%.zip}}"

echo "Syncing errorAnalysis to ${BABEL_LOGIN}:${BABEL_PROJECT_DIR}"
ssh "${BABEL_LOGIN}" "mkdir -p '${BABEL_PROJECT_DIR}' '${BABEL_PROJECT_DIR}/logs'"
rsync -az --delete \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'data/babel_outputs' \
  --exclude 'config/babel.env' \
  --exclude 'external' \
  --exclude 'logs' \
  "${REPO_ROOT}/" "${BABEL_LOGIN}:${BABEL_PROJECT_DIR}/"

if ! ssh "${BABEL_LOGIN}" "test -x '${BABEL_PROJECT_DIR}/.venv/bin/python'"; then
  echo "ERROR: Remote Python env missing at ${BABEL_PROJECT_DIR}/.venv" >&2
  echo "Create it once on Babel, then resubmit:" >&2
  echo "  ssh ${BABEL_LOGIN}" >&2
  echo "  cd ${BABEL_PROJECT_DIR} && scripts/babel/setup_env.sh" >&2
  exit 1
fi

SBATCH_ARGS=(--partition "${BABEL_PARTITION}" --time "${BABEL_TIME}" --cpus-per-task "${BABEL_CPUS}" --mem "${BABEL_MEM}")

if [[ -n "${BABEL_ACCOUNT:-}" ]]; then
  SBATCH_ARGS+=(--account "${BABEL_ACCOUNT}")
fi
if [[ -n "${BABEL_QOS:-}" ]]; then
  SBATCH_ARGS+=(--qos "${BABEL_QOS}")
fi
if [[ "${BABEL_GPUS}" != "0" && -n "${BABEL_GPUS}" ]]; then
  SBATCH_ARGS+=(--gres "gpu:${BABEL_GPU_TYPE}:${BABEL_GPUS}")
fi

REMOTE_CMD=$(cat <<EOF
cd '${BABEL_PROJECT_DIR}' &&
RUN_ID='${RUN_ID}' OSWORLD_PACKAGE='${OSWORLD_PACKAGE}' OSWORLD_MAX_EPISODES='${OSWORLD_MAX_EPISODES}' \
OSWORLD_PHASE='${OSWORLD_PHASE}' OSWORLD_FAILED_ONLY='${OSWORLD_FAILED_ONLY}' \
STAGE_NORMALIZED_TRACES='${STAGE_NORMALIZED_TRACES}' \
sbatch --export=ALL ${SBATCH_ARGS[*]} scripts/babel/analyze_hf_osworld.sbatch
EOF
)

echo "Submitting ${RUN_ID} for ${OSWORLD_PACKAGE}"
ssh "${BABEL_LOGIN}" "${REMOTE_CMD}"
echo "Submitted. Outputs will land under /data/user_data/${BABEL_USER}/cua_failure_analysis/outputs/${RUN_ID}"
