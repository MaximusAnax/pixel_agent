#!/usr/bin/env bash
#SBATCH --job-name=cua-hf-analysis
#SBATCH --output=/home/%u/cua-failure-analysis/logs/%x-%j.out
#SBATCH --error=/home/%u/cua-failure-analysis/logs/%x-%j.err

set -euo pipefail

_OVERRIDE_VARS=(
  RUN_ID OSWORLD_PACKAGE OSWORLD_MAX_EPISODES OSWORLD_PHASE
  OSWORLD_FAILED_ONLY OSWORLD_SELECT_TURN STAGE_NORMALIZED_TRACES HF_DOWNLOAD_MODE
  BABEL_OUTPUT_ROOT
)
declare -A _SUBMIT_OVERRIDE=()
for _v in "${_OVERRIDE_VARS[@]}"; do
  if [[ -n "${!_v+x}" ]]; then
    _SUBMIT_OVERRIDE["${_v}"]="${!_v}"
  fi
done

# Per-user secrets (API keys); not in the shared git clone.
for _babel_env in \
  "${HOME}/cua-failure-analysis/config/babel.env" \
  "${HOME}/.pixel_agent/babel.env"; do
  if [[ -f "${_babel_env}" ]]; then
    # shellcheck disable=SC1090
    source "${_babel_env}"
    break
  fi
done

for _v in "${_OVERRIDE_VARS[@]}"; do
  if [[ -n "${_SUBMIT_OVERRIDE[${_v}]+x}" ]]; then
    printf -v "${_v}" '%s' "${_SUBMIT_OVERRIDE[${_v}]}"
  fi
done

: "${BABEL_USER:=${USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_REPO:=${BABEL_GROUP_ROOT}/pixelAgent}"
: "${BABEL_SHARED_ERROR_ANALYSIS:=${BABEL_SHARED_REPO}/errorAnalysis}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_OUTPUT_MIRROR:=${BABEL_HOME_DIR}/cua-failure-analysis/data/babel_outputs}"
: "${BABEL_USER_DATA:=/data/user_data/${BABEL_USER}}"
: "${BABEL_DATA_ROOT:=${BABEL_USER_DATA}/cua_failure_analysis}"
: "${BABEL_RAW_ROOT:=${BABEL_DATA_ROOT}/hf_raw}"
: "${BABEL_OUTPUT_ROOT:=${BABEL_SHARED_OUTPUT_ROOT}}"
: "${BABEL_WORK_ROOT:=${BABEL_DATA_ROOT}/work}"
: "${BABEL_SHARED_DATASETS:=/data/datasets}"
: "${BABEL_SHARED_MODELS:=/data/models}"
: "${HF_HOME:=${BABEL_DATA_ROOT}/hf}"
: "${HF_HUB_CACHE:=${HF_HOME}/hub}"
: "${HF_DATASETS_CACHE:=${HF_HOME}/datasets}"
: "${OSWORLD_HF_REPO:=xlangai/ubuntu_osworld_verified_trajs}"
: "${OSWORLD_HF_REVISION:=main}"
: "${OSWORLD_PACKAGE:=opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip}"
: "${OSWORLD_MAX_EPISODES:=25}"
: "${OSWORLD_PHASE:=all}"
: "${OSWORLD_FAILED_ONLY:=0}"
: "${OSWORLD_SELECT_TURN:=turn_1}"
: "${HF_HUB_DISABLE_XET:=1}"

export HF_HOME HF_HUB_CACHE HF_DATASETS_CACHE HF_HUB_DISABLE_XET

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_${OSWORLD_PACKAGE%.zip}}"
OUTPUT_DIR="${BABEL_OUTPUT_ROOT}/${RUN_ID}"
JOB_WORK_ROOT="${BABEL_WORK_ROOT}/${SLURM_JOB_ID:-manual}_${RUN_ID}"
BABEL_PROJECT_DIR="${BABEL_SHARED_ERROR_ANALYSIS}"

mkdir -p "${BABEL_RAW_ROOT}" "${OUTPUT_DIR}" "${JOB_WORK_ROOT}" "${HF_HOME}" \
  "${BABEL_HOME_DIR}/cua-failure-analysis/logs" "${BABEL_OUTPUT_MIRROR}"

stat "/data/user_data/${BABEL_USER}" >/dev/null
stat "${BABEL_GROUP_ROOT}" >/dev/null
stat "${BABEL_SHARED_DATASETS}" >/dev/null || true
stat "${BABEL_SHARED_MODELS}" >/dev/null || true

cd "${BABEL_SHARED_ERROR_ANALYSIS}"

if [[ -n "${SLURM_JOB_GPUS:-}${SLURM_GPUS_ON_NODE:-}${CUDA_VISIBLE_DEVICES:-}" ]] \
   && command -v module >/dev/null 2>&1; then
  module load "${BABEL_CUDA_MODULE:-cuda-12.9}" || true
fi

echo "Run ID: ${RUN_ID}"
echo "Package: ${OSWORLD_PACKAGE}"
echo "Shared repo: ${BABEL_SHARED_REPO}"
echo "Output: ${OUTPUT_DIR}"
echo "Work root: ${JOB_WORK_ROOT}"
echo "HF_HOME: ${HF_HOME}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "${BABEL_SHARED_VENV}/bin/python" ]]; then
    PYTHON_BIN="${BABEL_SHARED_VENV}/bin/python"
  else
    echo "ERROR: ${BABEL_SHARED_VENV}/bin/python not found." >&2
    echo "Run: scripts/babel/init_shared_project.sh" >&2
    exit 1
  fi
fi

export PYTHONPATH="${BABEL_SHARED_ERROR_ANALYSIS}/src:${PYTHONPATH:-}"

"${PYTHON_BIN}" scripts/hf_osworld_analyze.py \
  --repo-id "${OSWORLD_HF_REPO}" \
  --revision "${OSWORLD_HF_REVISION}" \
  --package "${OSWORLD_PACKAGE}" \
  --raw-root "${BABEL_RAW_ROOT}" \
  --shared-datasets-root "${BABEL_SHARED_DATASETS}" \
  --work-root "${JOB_WORK_ROOT}" \
  --output-dir "${OUTPUT_DIR}" \
  --max-episodes "${OSWORLD_MAX_EPISODES}" \
  --phase "${OSWORLD_PHASE}" \
  --select-turn "${OSWORLD_SELECT_TURN}" \
  --taxonomy failureTaxonomy.md \
  --analysis-plan failureAnalysisFinalPlan.md \
  $([[ "${OSWORLD_FAILED_ONLY}" != "0" && -n "${OSWORLD_FAILED_ONLY}" ]] && echo --failed-only) \
  ${HF_DOWNLOAD_MODE:+--download-mode "${HF_DOWNLOAD_MODE}"} \
  ${JUDGE_PROVIDER:+--judge-provider "${JUDGE_PROVIDER}"} \
  ${JUDGE_BASE_URL:+--judge-base-url "${JUDGE_BASE_URL}"} \
  ${JUDGE_MODEL:+--judge-model "${JUDGE_MODEL}"} \
  ${ANTHROPIC_API_KEY:+--judge-api-key "${ANTHROPIC_API_KEY}"} \
  ${JUDGE_API_KEY:+--judge-api-key "${JUDGE_API_KEY}"} \
  ${JUDGE_MAX_CALLS:+--judge-max-calls "${JUDGE_MAX_CALLS}"}

echo "Analysis complete: ${OUTPUT_DIR}"
scripts/babel/stage_outputs_to_home.sh "${RUN_ID}"
