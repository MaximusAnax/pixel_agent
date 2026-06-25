#!/usr/bin/env bash
# Wait for a Babel analysis run to finish, exiting when summary.md exists or the
# Slurm job reaches a terminal failure state.
#
# Usage:
#   scripts/babel/wait_for_run.sh <slurm_job_id> <run_id>
#
# Exit 0 when remote summary.md exists.
# Exit 1 when the job failed/cancelled/timed out without producing summary.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@login.babel.cs.cmu.edu}"
: "${BABEL_DATA_ROOT:=/data/user_data/${BABEL_USER}/cua_failure_analysis}"
: "${POLL_INTERVAL_SEC:=120}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <slurm_job_id> <run_id>" >&2
  exit 2
fi

JOB_ID="$1"
RUN_ID="$2"
SUMMARY_PATH="${BABEL_DATA_ROOT}/outputs/${RUN_ID}/summary.md"
LOG_DIR="/home/${BABEL_USER}/cua-failure-analysis/logs"
FAIL_STATES="FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|PREEMPTED|BOOT_FAIL|DEADLINE"

remote_summary_exists() {
  ssh "${BABEL_LOGIN}" "test -f '${SUMMARY_PATH}'"
}

remote_job_state() {
  ssh "${BABEL_LOGIN}" "sacct -j '${JOB_ID}' -n -X --format=State 2>/dev/null | head -1 | tr -d ' '"
}

echo "Waiting for ${RUN_ID} (Slurm job ${JOB_ID})"
echo "  summary: ${SUMMARY_PATH}"
echo "  poll interval: ${POLL_INTERVAL_SEC}s"

while true; do
  if remote_summary_exists; then
    echo "DONE: ${SUMMARY_PATH} exists"
    exit 0
  fi

  state="$(remote_job_state || true)"
  if [[ -n "${state}" && "${state}" =~ ^(${FAIL_STATES})$ ]]; then
    echo "ERROR: Slurm job ${JOB_ID} ended with state ${state} and no summary.md" >&2
    echo "Check logs on Babel:" >&2
    echo "  ${LOG_DIR}/cua-hf-analysis-${JOB_ID}.out" >&2
    echo "  ${LOG_DIR}/cua-hf-analysis-${JOB_ID}.err" >&2
    exit 1
  fi

  if [[ "${state}" == "COMPLETED" ]]; then
    echo "ERROR: Slurm job ${JOB_ID} completed but ${SUMMARY_PATH} is missing" >&2
    echo "Check logs on Babel:" >&2
    echo "  ${LOG_DIR}/cua-hf-analysis-${JOB_ID}.out" >&2
    echo "  ${LOG_DIR}/cua-hf-analysis-${JOB_ID}.err" >&2
    exit 1
  fi

  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) still waiting (sacct state: ${state:-unknown})"
  sleep "${POLL_INTERVAL_SEC}"
done
