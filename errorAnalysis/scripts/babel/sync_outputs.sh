#!/usr/bin/env bash
# Pull compact Babel analysis artifacts back to the local workspace.
#
# Artifacts are written on compute-node storage first, then staged under
# ~/cua-failure-analysis/data/babel_outputs/<run_id> on home (login-visible).
# Legacy runs that skipped staging are copied via a short debug-partition srun.

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
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:10:00}"

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: scripts/babel/sync_outputs.sh <run_id>"
  exit 2
fi

REMOTE_DIR="${BABEL_STAGING_ROOT}/${RUN_ID}"
LOCAL_DIR="${REPO_ROOT}/data/babel_outputs/${RUN_ID}"

if ! ssh "${BABEL_LOGIN}" "test -f '${REMOTE_DIR}/summary.md'"; then
  echo "Staged summary not on login node; copying from compute storage via srun..."
  # Use --noprofile --norc: login shells on Babel may disable globbing (set -f),
  # which breaks "${src}/${pattern}" copies.
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=1 --mem=4G --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<EOF
set -euo pipefail
src="/data/user_data/${BABEL_USER}/cua_failure_analysis/outputs/${RUN_ID}"
dst="${REMOTE_DIR}"
if [[ ! -d "\${src}" ]]; then echo "ERROR: missing \${src}" >&2; exit 1; fi
mkdir -p "\${dst}"
copied=0
for file in "\${src}"/*.json "\${src}"/*.jsonl "\${src}"/*.csv "\${src}"/*.md; do
  [[ -e "\${file}" ]] || continue
  cp -a "\${file}" "\${dst}/"
  copied=\$((copied + 1))
done
if [[ "\${copied}" -eq 0 ]]; then echo "ERROR: no artifacts in \${src}" >&2; exit 1; fi
test -f "\${dst}/summary.md"
echo "Staged \${copied} file(s) to \${dst}"
EOF
fi

mkdir -p "${LOCAL_DIR}"

# Compact artifacts (json/jsonl/csv/md) are always pulled. Set
# SYNC_NORMALIZED_TRACES=1 to also pull the per-episode normalized_traces/ tree
# (only present when staged with STAGE_NORMALIZED_TRACES=1).
: "${SYNC_NORMALIZED_TRACES:=0}"

RSYNC_INCLUDES=(
  --include '*/'
  --include '*.json'
  --include '*.jsonl'
  --include '*.csv'
  --include '*.md'
)
if [[ "${SYNC_NORMALIZED_TRACES}" != "0" ]]; then
  RSYNC_INCLUDES+=(--include 'normalized_traces/**')
fi

rsync -az \
  "${RSYNC_INCLUDES[@]}" \
  --exclude '*' \
  "${BABEL_LOGIN}:${REMOTE_DIR}/" "${LOCAL_DIR}/"

echo "Synced ${RUN_ID} to ${LOCAL_DIR}"
