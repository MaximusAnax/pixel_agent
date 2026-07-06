#!/usr/bin/env bash
# Submit a Phase 1 HF OSWorld failure-analysis job to Babel.
#
# Uses the shared mattlab pixel_agent repo clone (not per-user home rsync).
#
# Usage:
#   cp config/babel.env.example config/babel.env
#   source config/babel.env
#   git push   # from pixelAgent repo root
#   scripts/babel/submit_hf_analysis.sh opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

_CALLER_RUN_ID="${RUN_ID:-}"
_CALLER_OSWORLD_PACKAGE="${OSWORLD_PACKAGE:-}"
_CALLER_OSWORLD_MAX_EPISODES="${OSWORLD_MAX_EPISODES:-}"
_CALLER_OSWORLD_PHASE="${OSWORLD_PHASE:-}"
_CALLER_OSWORLD_FAILED_ONLY="${OSWORLD_FAILED_ONLY:-}"
_CALLER_OSWORLD_SELECT_TURN="${OSWORLD_SELECT_TURN:-}"
_CALLER_STAGE_NORMALIZED_TRACES="${STAGE_NORMALIZED_TRACES:-}"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

if [[ -n "${_CALLER_RUN_ID}" ]]; then RUN_ID="${_CALLER_RUN_ID}"; fi
if [[ -n "${_CALLER_OSWORLD_PACKAGE}" ]]; then OSWORLD_PACKAGE="${_CALLER_OSWORLD_PACKAGE}"; fi
if [[ -n "${_CALLER_OSWORLD_MAX_EPISODES}" ]]; then OSWORLD_MAX_EPISODES="${_CALLER_OSWORLD_MAX_EPISODES}"; fi
if [[ -n "${_CALLER_OSWORLD_PHASE}" ]]; then OSWORLD_PHASE="${_CALLER_OSWORLD_PHASE}"; fi
if [[ -n "${_CALLER_OSWORLD_FAILED_ONLY}" ]]; then OSWORLD_FAILED_ONLY="${_CALLER_OSWORLD_FAILED_ONLY}"; fi
if [[ -n "${_CALLER_OSWORLD_SELECT_TURN}" ]]; then OSWORLD_SELECT_TURN="${_CALLER_OSWORLD_SELECT_TURN}"; fi
if [[ -n "${_CALLER_STAGE_NORMALIZED_TRACES}" ]]; then STAGE_NORMALIZED_TRACES="${_CALLER_STAGE_NORMALIZED_TRACES}"; fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@login.babel.cs.cmu.edu}"
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_REPO:=${BABEL_GROUP_ROOT}/pixelAgent}"
: "${BABEL_SHARED_ERROR_ANALYSIS:=${BABEL_SHARED_REPO}/errorAnalysis}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"
: "${BABEL_PARTITION:=cpu}"
: "${BABEL_TIME:=06:00:00}"
: "${BABEL_CPUS:=8}"
: "${BABEL_MEM:=64G}"
: "${BABEL_GPUS:=0}"
: "${BABEL_GPU_TYPE:=L40S}"
: "${OSWORLD_PACKAGE:=${1:-opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip}}"
: "${OSWORLD_MAX_EPISODES:=25}"
: "${OSWORLD_PHASE:=all}"
: "${OSWORLD_FAILED_ONLY:=0}"
: "${OSWORLD_SELECT_TURN:=turn_1}"
: "${STAGE_NORMALIZED_TRACES:=0}"

if [[ $# -ge 1 ]]; then
  OSWORLD_PACKAGE="$1"
fi

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_${OSWORLD_PACKAGE%.zip}}"

echo "Updating shared repo on Babel..."
"${SCRIPT_DIR}/sync_shared_repo.sh" pull

LOG_DIR="${BABEL_HOME_DIR}/cua-failure-analysis/logs"
ssh "${BABEL_LOGIN}" "mkdir -p '${LOG_DIR}'"

if ! ssh "${BABEL_LOGIN}" "srun --partition=debug --cpus-per-task=1 --mem=4G --time=00:05:00 -n1 \
  test -x '${BABEL_SHARED_VENV}/bin/python'"; then
  echo "ERROR: Shared Python env missing at ${BABEL_SHARED_VENV}/bin/python" >&2
  echo "Run once: scripts/babel/init_shared_project.sh" >&2
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

SBATCH_EXPORT="ALL,RUN_ID=${RUN_ID},OSWORLD_PACKAGE=${OSWORLD_PACKAGE},OSWORLD_MAX_EPISODES=${OSWORLD_MAX_EPISODES},OSWORLD_PHASE=${OSWORLD_PHASE},OSWORLD_FAILED_ONLY=${OSWORLD_FAILED_ONLY},OSWORLD_SELECT_TURN=${OSWORLD_SELECT_TURN},STAGE_NORMALIZED_TRACES=${STAGE_NORMALIZED_TRACES},BABEL_OUTPUT_ROOT=${BABEL_SHARED_OUTPUT_ROOT}"

REMOTE_CMD=$(cat <<EOF
cd '${BABEL_SHARED_ERROR_ANALYSIS}' &&
sbatch --export='${SBATCH_EXPORT}' ${SBATCH_ARGS[*]} scripts/babel/analyze_hf_osworld.sbatch
EOF
)

echo "Submitting ${RUN_ID} for ${OSWORLD_PACKAGE}"
ssh "${BABEL_LOGIN}" "${REMOTE_CMD}"
echo "Submitted. Shared outputs: ${BABEL_SHARED_OUTPUT_ROOT}/${RUN_ID}"
