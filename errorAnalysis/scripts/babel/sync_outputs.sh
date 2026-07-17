#!/usr/bin/env bash
# Pull compact Babel analysis artifacts back to the local workspace.
#
# Canonical storage: /data/group_data/mattlab/pixel_agent/outputs/<run_id>
# Mirrored to home via stage_outputs_to_home.sh for login-node rsync.

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
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_OUTPUT_MIRROR:=${BABEL_HOME_DIR}/cua-failure-analysis/data/babel_outputs}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:10:00}"

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: scripts/babel/sync_outputs.sh <run_id>"
  exit 2
fi

REMOTE_DIR="${BABEL_OUTPUT_MIRROR}/${RUN_ID}"
LOCAL_DIR="${REPO_ROOT}/data/babel_outputs/${RUN_ID}"

if ! ssh "${BABEL_LOGIN}" "test -f '${REMOTE_DIR}/summary.md'"; then
  echo "Staged summary not on login node; copying from shared group outputs via srun..."
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=1 --mem=4G --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<EOF
set -euo pipefail
src="${BABEL_SHARED_OUTPUT_ROOT}/${RUN_ID}"
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
