#!/usr/bin/env bash
# Update the shared pixelAgent git clone on Babel (compute node).
#
# Push from your laptop to GitHub first, then pull on Babel:
#   git push
#   scripts/babel/sync_shared_repo.sh pull
#
# Usage:
#   scripts/babel/sync_shared_repo.sh pull
#   scripts/babel/sync_shared_repo.sh status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_ROOT}/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_LOGIN:=andiongu@login.babel.cs.cmu.edu}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_REPO:=${BABEL_GROUP_ROOT}/pixelAgent}"
: "${BABEL_SHARED_BRANCH:=feat/starting-failure-analysis}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:10:00}"
: "${BABEL_STAGE_MEM:=4G}"

ACTION="${1:-pull}"

if [[ "${ACTION}" != "pull" && "${ACTION}" != "status" ]]; then
  echo "Usage: scripts/babel/sync_shared_repo.sh {pull|status}" >&2
  exit 2
fi

_run_on_compute() {
  local remote_cmd="$1"
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=1 \
    --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<< "${remote_cmd}"
}

if [[ "${ACTION}" == "status" ]]; then
  remote_cmd=$(cat <<EOF
set -euo pipefail
if [[ ! -d '${BABEL_SHARED_REPO}/.git' ]]; then
  echo "ERROR: shared repo not initialized. Run scripts/babel/init_shared_project.sh" >&2
  exit 1
fi
cd '${BABEL_SHARED_REPO}'
echo "branch: \$(git rev-parse --abbrev-ref HEAD)"
echo "commit: \$(git rev-parse --short HEAD)"
echo "remote: \$(git remote get-url origin 2>/dev/null || echo n/a)"
git status -sb
EOF
)
  _run_on_compute "${remote_cmd}"
  exit 0
fi

remote_cmd=$(cat <<EOF
set -euo pipefail
if [[ ! -d '${BABEL_SHARED_REPO}/.git' ]]; then
  echo "ERROR: shared repo not found at ${BABEL_SHARED_REPO}" >&2
  echo "Run: scripts/babel/init_shared_project.sh" >&2
  exit 1
fi
cd '${BABEL_SHARED_REPO}'
git fetch origin
git checkout '${BABEL_SHARED_BRANCH}'
git pull --ff-only origin '${BABEL_SHARED_BRANCH}' || git pull --ff-only
echo "Updated ${BABEL_SHARED_REPO}"
echo "branch: \$(git rev-parse --abbrev-ref HEAD) @ \$(git rev-parse --short HEAD)"
EOF
)

echo "Pulling ${BABEL_SHARED_BRANCH} on Babel shared repo..."
_run_on_compute "${remote_cmd}"
