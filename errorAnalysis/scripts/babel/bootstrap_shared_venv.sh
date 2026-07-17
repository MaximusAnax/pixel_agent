#!/usr/bin/env bash
# (Re)create the shared Python venv at BABEL_SHARED_VENV on a compute node.
#
# Use after init_shared_project if the venv landed under errorAnalysis/.venv
# or if dependencies are missing (e.g. ModuleNotFoundError: pydantic).
#
# Usage (from errorAnalysis/ on laptop):
#   source config/babel.env
#   scripts/babel/bootstrap_shared_venv.sh

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
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:30:00}"
: "${BABEL_STAGE_MEM:=8G}"

remote_cmd=$(cat <<EOF
set -euo pipefail
cd '${BABEL_SHARED_ERROR_ANALYSIS}'
export BABEL_PROJECT_DIR='${BABEL_SHARED_ERROR_ANALYSIS}'
export BABEL_VENV_PATH='${BABEL_SHARED_VENV}'
bash scripts/babel/setup_env.sh
'${BABEL_SHARED_VENV}'/bin/python -c 'import pydantic; print("pydantic ok")'
EOF
)

echo "Bootstrapping shared venv at ${BABEL_SHARED_VENV}..."
ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=2 \
  --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
  bash --noprofile --norc -s" <<< "${remote_cmd}"
echo "Done: ${BABEL_SHARED_VENV}/bin/python"
