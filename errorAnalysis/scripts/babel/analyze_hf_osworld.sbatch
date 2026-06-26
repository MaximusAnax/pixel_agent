#!/usr/bin/env bash
#SBATCH --job-name=cua-hf-analysis
#SBATCH --output=/home/andiongu/cua-failure-analysis/logs/%x-%j.out
#SBATCH --error=/home/andiongu/cua-failure-analysis/logs/%x-%j.err

set -euo pipefail

if [[ -f "${HOME}/cua-failure-analysis/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/cua-failure-analysis/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_PROJECT_DIR:=/home/${BABEL_USER}/cua-failure-analysis}"
: "${BABEL_DATA_ROOT:=/data/user_data/${BABEL_USER}/cua_failure_analysis}"
: "${BABEL_RAW_ROOT:=${BABEL_DATA_ROOT}/hf_raw}"
: "${BABEL_OUTPUT_ROOT:=${BABEL_DATA_ROOT}/outputs}"
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

export HF_HOME HF_HUB_CACHE HF_DATASETS_CACHE

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_${OSWORLD_PACKAGE%.zip}}"
OUTPUT_DIR="${BABEL_OUTPUT_ROOT}/${RUN_ID}"
JOB_WORK_ROOT="${BABEL_WORK_ROOT}/${SLURM_JOB_ID:-manual}_${RUN_ID}"

mkdir -p "${BABEL_RAW_ROOT}" "${OUTPUT_DIR}" "${JOB_WORK_ROOT}" "${HF_HOME}" "${BABEL_PROJECT_DIR}/logs"

# Trigger AutoFS mounts with full paths. Some Babel network directories appear
# empty until touched by their complete path.
stat "/data/user_data/${BABEL_USER}" >/dev/null
stat "${BABEL_SHARED_DATASETS}" >/dev/null || true
stat "${BABEL_SHARED_MODELS}" >/dev/null || true

cd "${BABEL_PROJECT_DIR}"

# Load CUDA only when this job actually has GPUs (per the quickstart guide:
# `module load cuda-12.9`). CPU-only Phase 1 analysis skips this.
if [[ -n "${SLURM_JOB_GPUS:-}${SLURM_GPUS_ON_NODE:-}${CUDA_VISIBLE_DEVICES:-}" ]] \
   && command -v module >/dev/null 2>&1; then
  module load "${BABEL_CUDA_MODULE:-cuda-12.9}" || true
fi

echo "Run ID: ${RUN_ID}"
echo "Package: ${OSWORLD_PACKAGE}"
echo "Output: ${OUTPUT_DIR}"
echo "Work root: ${JOB_WORK_ROOT}"
echo "HF_HOME: ${HF_HOME}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "${BABEL_PROJECT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${BABEL_PROJECT_DIR}/.venv/bin/python"
  else
    echo "ERROR: ${BABEL_PROJECT_DIR}/.venv/bin/python not found." >&2
    echo "Run on Babel: cd ${BABEL_PROJECT_DIR} && scripts/babel/setup_env.sh" >&2
    exit 1
  fi
fi

export PYTHONPATH="${BABEL_PROJECT_DIR}/src:${PYTHONPATH:-}"

"${PYTHON_BIN}" scripts/hf_osworld_analyze.py \
  --repo-id "${OSWORLD_HF_REPO}" \
  --revision "${OSWORLD_HF_REVISION}" \
  --package "${OSWORLD_PACKAGE}" \
  --raw-root "${BABEL_RAW_ROOT}" \
  --shared-datasets-root "${BABEL_SHARED_DATASETS}" \
  --work-root "${JOB_WORK_ROOT}" \
  --output-dir "${OUTPUT_DIR}" \
  --max-episodes "${OSWORLD_MAX_EPISODES}" \
  --taxonomy failureTaxonomy.md \
  --analysis-plan failureAnalysisFinalPlan.md \
  ${HF_DOWNLOAD_MODE:+--download-mode "${HF_DOWNLOAD_MODE}"} \
  ${JUDGE_BASE_URL:+--judge-base-url "${JUDGE_BASE_URL}"} \
  ${JUDGE_MODEL:+--judge-model "${JUDGE_MODEL}"} \
  ${JUDGE_API_KEY:+--judge-api-key "${JUDGE_API_KEY}"}

echo "Analysis complete: ${OUTPUT_DIR}"
scripts/babel/stage_outputs_to_home.sh "${RUN_ID}"
