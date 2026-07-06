#!/usr/bin/env bash
# Pull a Babel-built trace review packet to the local workspace.
#
# Packets are built on compute storage and mirrored to home staging for login
# rsync. Group canonical path: ${BABEL_PACKET_STAGING}/<packet_id>
#
# Usage:
#   scripts/babel/sync_review_packet.sh pilot_taxonomy_paired_20260703

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
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_PACKET_STAGING:=${BABEL_GROUP_ROOT}/review_packets}"
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_REVIEW_STAGING:=${BABEL_HOME_DIR}/cua-failure-analysis/data/review_packets}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:15:00}"
: "${BABEL_STAGE_MEM:=8G}"

PACKET_ID="${1:-}"
if [[ -z "${PACKET_ID}" ]]; then
  echo "Usage: scripts/babel/sync_review_packet.sh <packet_id>" >&2
  exit 2
fi

REMOTE_GROUP_DIR="${BABEL_PACKET_STAGING}/${PACKET_ID}"
REMOTE_MIRROR_DIR="${BABEL_REVIEW_STAGING}/${PACKET_ID}"
LOCAL_DIR="${REPO_ROOT}/data/review_packets/${PACKET_ID}"

_run_on_compute() {
  local remote_cmd="$1"
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=2 \
    --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<< "${remote_cmd}"
}

remote_cmd=$(cat <<EOF
set -euo pipefail
mkdir -p '${REMOTE_MIRROR_DIR}'
if [[ -f '${REMOTE_GROUP_DIR}/index.html' ]]; then
  rsync -a --delete '${REMOTE_GROUP_DIR}/' '${REMOTE_MIRROR_DIR}/'
  echo "Mirrored packet from group staging to home"
elif [[ -f '${REMOTE_MIRROR_DIR}/index.html' ]]; then
  echo "Using existing home mirror (group packet absent)"
else
  echo "ERROR: packet not found at ${REMOTE_GROUP_DIR} or ${REMOTE_MIRROR_DIR}" >&2
  exit 1
fi
EOF
)

echo "Staging packet ${PACKET_ID} on Babel for login rsync..."
_run_on_compute "${remote_cmd}"

if ! ssh "${BABEL_LOGIN}" "test -f '${REMOTE_MIRROR_DIR}/index.html'"; then
  echo "ERROR: staged packet not found at ${REMOTE_MIRROR_DIR}/index.html" >&2
  echo "Run scripts/babel/build_review_packet.sh first." >&2
  exit 1
fi

mkdir -p "${LOCAL_DIR}"
rsync -az "${BABEL_LOGIN}:${REMOTE_MIRROR_DIR}/" "${LOCAL_DIR}/"

if [[ -f "${LOCAL_DIR}/taxonomy_discovery_labels.csv" ]]; then
  cp "${LOCAL_DIR}/taxonomy_discovery_labels.csv" \
    "${REPO_ROOT}/data/labeling/taxonomy_discovery_labels.csv"
fi

echo "Synced review packet to ${LOCAL_DIR}"
echo "Open: file://${LOCAL_DIR}/index.html"
