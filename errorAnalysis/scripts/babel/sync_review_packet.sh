#!/usr/bin/env bash
# Pull a Babel-built trace review packet to the local workspace.
#
# Usage:
#   scripts/babel/sync_review_packet.sh pilot_taxonomy_20260630

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
: "${BABEL_REVIEW_STAGING:=${BABEL_PROJECT_DIR}/data/review_packets}"

PACKET_ID="${1:-}"
if [[ -z "${PACKET_ID}" ]]; then
  echo "Usage: scripts/babel/sync_review_packet.sh <packet_id>" >&2
  exit 2
fi

REMOTE_DIR="${BABEL_REVIEW_STAGING}/${PACKET_ID}"
LOCAL_DIR="${REPO_ROOT}/data/review_packets/${PACKET_ID}"

if ! ssh "${BABEL_LOGIN}" "test -f '${REMOTE_DIR}/index.html'"; then
  echo "ERROR: staged packet not found at ${REMOTE_DIR}/index.html" >&2
  echo "Run scripts/babel/build_review_packet.sh first." >&2
  exit 1
fi

mkdir -p "${LOCAL_DIR}"
rsync -az "${BABEL_LOGIN}:${REMOTE_DIR}/" "${LOCAL_DIR}/"

# Also pull discovery worksheet into data/labeling for convenience
if [[ -f "${LOCAL_DIR}/taxonomy_discovery_labels.csv" ]]; then
  cp "${LOCAL_DIR}/taxonomy_discovery_labels.csv" \
    "${REPO_ROOT}/data/labeling/taxonomy_discovery_labels.csv"
fi

echo "Synced review packet to ${LOCAL_DIR}"
echo "Open: file://${LOCAL_DIR}/index.html"
