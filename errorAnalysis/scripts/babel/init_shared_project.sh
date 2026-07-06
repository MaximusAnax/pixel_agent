#!/usr/bin/env bash
# One-time setup of the shared mattlab pixel_agent project root on Babel.
#
# Creates group dirs, clones the full pixelAgent repo, and bootstraps a shared
# Python venv on a compute node.
#
# Usage (from errorAnalysis/ on laptop):
#   source config/babel.env
#   scripts/babel/init_shared_project.sh

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
: "${BABEL_SHARED_ERROR_ANALYSIS:=${BABEL_SHARED_REPO}/errorAnalysis}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"
: "${BABEL_SHARED_BRANCH:=feat/starting-failure-analysis}"
: "${BABEL_SHARED_GIT_URL:=git@github.com:MaximusAnax/pixel_agent.git}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:30:00}"
: "${BABEL_STAGE_MEM:=8G}"

_EFFECTIVE_GIT_URL="${BABEL_SHARED_GIT_URL}"
if [[ -n "${BABEL_GIT_TOKEN:-}" && "${_EFFECTIVE_GIT_URL}" == https://* ]]; then
  _EFFECTIVE_GIT_URL="https://x-access-token:${BABEL_GIT_TOKEN}@${_EFFECTIVE_GIT_URL#https://}"
fi

_run_on_compute() {
  local remote_cmd="$1"
  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=2 \
    --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<< "${remote_cmd}"
}

remote_cmd=$(cat <<EOF
set -euo pipefail

mkdir -p '${BABEL_GROUP_ROOT}' \\
  '${BABEL_SHARED_OUTPUT_ROOT}' \\
  '${BABEL_GROUP_ROOT}/review_packets' \\
  '${BABEL_GROUP_ROOT}/review_annotations' \\
  '${BABEL_GROUP_ROOT}/labeling' \\
  '${BABEL_GROUP_ROOT}/logs'

mkdir -p "\${HOME}/.ssh"
chmod 700 "\${HOME}/.ssh"
if [[ ! -f "\${HOME}/.ssh/known_hosts" ]] || ! grep -q '^github.com ' "\${HOME}/.ssh/known_hosts" 2>/dev/null; then
  ssh-keyscan -t ed25519,rsa github.com >> "\${HOME}/.ssh/known_hosts" 2>/dev/null || true
fi

GIT_URL='${_EFFECTIVE_GIT_URL}'

if [[ -d '${BABEL_SHARED_REPO}/.git' ]]; then
  echo "Shared repo already exists at ${BABEL_SHARED_REPO}"
elif [[ -d '${BABEL_SHARED_REPO}' ]]; then
  echo "Removing incomplete clone at ${BABEL_SHARED_REPO}" >&2
  rm -rf '${BABEL_SHARED_REPO}'
fi

if [[ ! -d '${BABEL_SHARED_REPO}/.git' ]]; then
  git clone "\${GIT_URL}" '${BABEL_SHARED_REPO}'
fi

cd '${BABEL_SHARED_REPO}'
git fetch origin
git checkout '${BABEL_SHARED_BRANCH}'
git pull --ff-only origin '${BABEL_SHARED_BRANCH}' || git pull --ff-only

cd '${BABEL_SHARED_ERROR_ANALYSIS}'
export BABEL_PROJECT_DIR='${BABEL_SHARED_ERROR_ANALYSIS}'
export BABEL_VENV_PATH='${BABEL_SHARED_VENV}'
bash scripts/babel/setup_env.sh

touch '${BABEL_GROUP_ROOT}/.write_test' && rm '${BABEL_GROUP_ROOT}/.write_test'

printf '%s\n' \
  '# Shared mattlab pixel_agent project' \
  "Initialized: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '' \
  '## Paths' \
  '' \
  "- Repo: ${BABEL_SHARED_REPO}" \
  "- errorAnalysis: ${BABEL_SHARED_ERROR_ANALYSIS}" \
  "- Shared outputs: ${BABEL_SHARED_OUTPUT_ROOT}" \
  "- Review packets: ${BABEL_GROUP_ROOT}/review_packets" \
  "- Annotations: ${BABEL_GROUP_ROOT}/review_annotations" \
  "- Python venv: ${BABEL_SHARED_VENV}" \
  '' \
  '## Daily sync (each person, from laptop)' \
  '' \
  'git push' \
  'scripts/babel/sync_shared_repo.sh pull' \
  '' \
  '## Repair venv' \
  '' \
  'scripts/babel/bootstrap_shared_venv.sh' \
  > '${BABEL_GROUP_ROOT}/BABEL_SETUP.md'

echo "Shared project ready at ${BABEL_GROUP_ROOT}"
echo "Branch: \$(cd '${BABEL_SHARED_REPO}' && git rev-parse --abbrev-ref HEAD) @ \$(cd '${BABEL_SHARED_REPO}' && git rev-parse --short HEAD)"
EOF
)

echo "Initializing shared mattlab project on Babel (srun ${BABEL_STAGE_PARTITION})..."
_run_on_compute "${remote_cmd}"
echo "Done. See ${BABEL_GROUP_ROOT}/BABEL_SETUP.md on Babel."
