#!/usr/bin/env bash
# Wait for a Babel analysis run to finish, exiting when summary.md exists or the
# Slurm job reaches a terminal failure state.
#
# Usage:
#   scripts/babel/wait_for_run.sh <slurm_job_id> <run_id>
#
# Exit 0 when staged summary.md exists on the login-visible home path (or the job
# log reports analysis complete for legacy runs).
# Exit 1 when the job failed/cancelled/timed out without producing outputs.

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
: "${BABEL_STAGING_ROOT:=${BABEL_PROJECT_DIR}/data/babel_outputs}"
: "${POLL_INTERVAL_SEC:=120}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <slurm_job_id> <run_id>" >&2
  exit 2
fi

JOB_ID="$1"
RUN_ID="$2"
STAGING_SUMMARY="${BABEL_STAGING_ROOT}/${RUN_ID}/summary.md"
LOG_OUT="${BABEL_PROJECT_DIR}/logs/cua-hf-analysis-${JOB_ID}.out"
FAIL_STATES="FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|PREEMPTED|BOOT_FAIL|DEADLINE"

remote_summary_exists() {
  ssh "${BABEL_LOGIN}" "test -f '${STAGING_SUMMARY}'"
}

remote_job_state() {
  ssh "${BABEL_LOGIN}" "sacct -j '${JOB_ID}' -n -X --format=State 2>/dev/null | head -1 | tr -d ' '"
}

remote_log_reports_complete() {
  ssh "${BABEL_LOGIN}" "grep -q 'Analysis complete:.*${RUN_ID}' '${LOG_OUT}' 2>/dev/null"
}

echo "Waiting for ${RUN_ID} (Slurm job ${JOB_ID})"
echo "  staged summary: ${STAGING_SUMMARY}"
echo "  poll interval: ${POLL_INTERVAL_SEC}s"

while true; do
  if remote_summary_exists; then
    echo "DONE: ${STAGING_SUMMARY} exists"
    exit 0
  fi

  state="$(remote_job_state || true)"
  if [[ -n "${state}" && "${state}" =~ ^(${FAIL_STATES})$ ]]; then
    echo "ERROR: Slurm job ${JOB_ID} ended with state ${state} and no staged summary.md" >&2
    echo "Check logs on Babel:" >&2
    echo "  ${LOG_OUT}" >&2
    echo "  ${BABEL_PROJECT_DIR}/logs/cua-hf-analysis-${JOB_ID}.err" >&2
    exit 1
  fi

  if [[ "${state}" == "COMPLETED" ]]; then
    if remote_log_reports_complete; then
      echo "DONE: job ${JOB_ID} completed (log confirms analysis). Staged summary not on login yet."
      echo "Run: scripts/babel/sync_outputs.sh ${RUN_ID}  # will stage from compute if needed"
      exit 0
    fi
    echo "ERROR: Slurm job ${JOB_ID} completed but no staged summary or success log line" >&2
    echo "Check logs on Babel:" >&2
    echo "  ${LOG_OUT}" >&2
    echo "  ${BABEL_PROJECT_DIR}/logs/cua-hf-analysis-${JOB_ID}.err" >&2
    exit 1
  fi

  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) still waiting (sacct state: ${state:-unknown})"
  sleep "${POLL_INTERVAL_SEC}"
done
