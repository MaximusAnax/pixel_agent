#!/usr/bin/env bash
# Pull or push shared multi-annotator annotations.json via Babel.
#
# Group data lives on compute nodes; this script mirrors through home staging
# (login-visible) using srun when BABEL_ANNOTATIONS_ROOT is set.
#
# Usage:
#   scripts/babel/sync_annotations.sh pull pilot_taxonomy_paired_20260703
#   scripts/babel/sync_annotations.sh push pilot_taxonomy_paired_20260703

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
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_ANNOTATIONS_ROOT:=${BABEL_GROUP_ROOT}/review_annotations}"
: "${BABEL_ANNOTATIONS_MIRROR:=${BABEL_HOME_DIR}/cua-failure-analysis/data/review_annotations}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:10:00}"
: "${BABEL_STAGE_MEM:=4G}"

ACTION="${1:-}"
PACKET_ID="${2:-}"

if [[ "${ACTION}" != "pull" && "${ACTION}" != "push" ]]; then
  echo "Usage: scripts/babel/sync_annotations.sh {pull|push} <packet_id>" >&2
  exit 2
fi

if [[ -z "${PACKET_ID}" ]]; then
  echo "Usage: scripts/babel/sync_annotations.sh {pull|push} <packet_id>" >&2
  exit 2
fi

REMOTE_GROUP_DIR="${BABEL_ANNOTATIONS_ROOT}/${PACKET_ID}"
REMOTE_GROUP_FILE="${REMOTE_GROUP_DIR}/annotations.json"
REMOTE_MIRROR_DIR="${BABEL_ANNOTATIONS_MIRROR}/${PACKET_ID}"
REMOTE_MIRROR_FILE="${REMOTE_MIRROR_DIR}/annotations.json"
LOCAL_DIR="${REPO_ROOT}/data/review_packets/${PACKET_ID}"
LOCAL_FILE="${LOCAL_DIR}/annotations.json"

_run_on_compute() {
  local remote_cmd="$1"
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=1 \
    --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<< "${remote_cmd}"
}

_pull_from_babel() {
  local remote_cmd
  remote_cmd=$(cat <<EOF
set -euo pipefail
mkdir -p '${REMOTE_MIRROR_DIR}'
if [[ -f '${REMOTE_GROUP_FILE}' ]]; then
  cp -a '${REMOTE_GROUP_FILE}' '${REMOTE_MIRROR_FILE}'
  echo "Mirrored group annotations to home staging"
elif [[ -f '${REMOTE_MIRROR_FILE}' ]]; then
  echo "Using existing home mirror (group file absent)"
else
  echo "No remote annotations yet; starting empty on next save"
  exit 0
fi
EOF
)
  _run_on_compute "${remote_cmd}"

  if ssh "${BABEL_LOGIN}" "test -f '${REMOTE_MIRROR_FILE}'"; then
    mkdir -p "${LOCAL_DIR}"
    rsync -az "${BABEL_LOGIN}:${REMOTE_MIRROR_FILE}" "${LOCAL_FILE}"
    echo "Pulled annotations -> ${LOCAL_FILE}"
  else
    echo "No annotations on Babel yet for ${PACKET_ID}"
  fi
}

_push_to_babel() {
  if [[ ! -f "${LOCAL_FILE}" ]]; then
    echo "ERROR: local annotations not found: ${LOCAL_FILE}" >&2
    exit 1
  fi

  mkdir -p "${LOCAL_DIR}"
  rsync -az "${LOCAL_FILE}" "${BABEL_LOGIN}:${REMOTE_MIRROR_FILE}"

  local remote_cmd ts backup
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="${REMOTE_GROUP_DIR}/annotations.json.bak.${ts}"
  remote_cmd=$(cat <<EOF
set -euo pipefail
mkdir -p '${REMOTE_GROUP_DIR}'
if [[ -f '${REMOTE_GROUP_FILE}' ]]; then
  cp -a '${REMOTE_GROUP_FILE}' '${backup}'
fi
cp -a '${REMOTE_MIRROR_FILE}' '${REMOTE_GROUP_FILE}'
echo "Pushed annotations to ${REMOTE_GROUP_FILE}"
EOF
)
  _run_on_compute "${remote_cmd}"
  echo "Pushed annotations to Babel group path for ${PACKET_ID}"
}

case "${ACTION}" in
  pull) _pull_from_babel ;;
  push) _push_to_babel ;;
esac
