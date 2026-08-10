#!/usr/bin/env bash
# Publish compact analysis artifacts to the shared mattlab outputs tree.
#
# Use when runs were produced before the shared layout (home mirror or user_data)
# but jobs like build_review_packet.sh read from BABEL_SHARED_OUTPUT_ROOT.
#
# Usage (from errorAnalysis/ on laptop):
#   source config/babel.env
#   scripts/babel/publish_outputs_to_shared.sh <run_id> [<run_id> ...]
#
# Example (v4 pilot runs):
#   scripts/babel/publish_outputs_to_shared.sh \
#     20260626_172919_a3b_pilot_full_v4 \
#     20260626_172922_7b_pilot_full_v4

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
: "${BABEL_USER_DATA:=/data/user_data/${BABEL_USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_OUTPUT_MIRROR:=${BABEL_HOME_DIR}/cua-failure-analysis/data/babel_outputs}"
: "${BABEL_DATA_ROOT:=${BABEL_USER_DATA}/cua_failure_analysis}"
: "${BABEL_LEGACY_OUTPUT_ROOT:=${BABEL_DATA_ROOT}/outputs}"
: "${BABEL_STAGE_PARTITION:=debug}"
: "${BABEL_STAGE_TIME:=00:15:00}"
: "${BABEL_STAGE_MEM:=4G}"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/babel/publish_outputs_to_shared.sh <run_id> [<run_id> ...]" >&2
  exit 2
fi

publish_one() {
  local run_id="$1"
  echo "Publishing ${run_id} -> ${BABEL_SHARED_OUTPUT_ROOT}/${run_id} ..."

  local remote_cmd
  remote_cmd=$(cat <<EOF
set -euo pipefail
run_id='${run_id}'
dst='${BABEL_SHARED_OUTPUT_ROOT}/'\${run_id}
mirror='${BABEL_OUTPUT_MIRROR}/'\${run_id}
legacy='${BABEL_LEGACY_OUTPUT_ROOT}/'\${run_id}

src=""
for candidate in "\${mirror}" "\${legacy}"; do
  if [[ -f "\${candidate}/episode_manifests.json" ]]; then
    src="\${candidate}"
    break
  fi
done

if [[ -z "\${src}" ]]; then
  echo "ERROR: no episode_manifests.json for \${run_id}" >&2
  echo "  checked: \${mirror}" >&2
  echo "  checked: \${legacy}" >&2
  exit 1
fi

if [[ -f "\${dst}/episode_manifests.json" ]]; then
  echo "  note: overwriting existing shared copy at \${dst}"
fi

mkdir -p "\${dst}"
copied=0
for file in "\${src}"/*.json "\${src}"/*.jsonl "\${src}"/*.csv "\${src}"/*.md; do
  [[ -e "\${file}" ]] || continue
  cp -a "\${file}" "\${dst}/"
  copied=\$((copied + 1))
done

if [[ "\${copied}" -eq 0 ]]; then
  echo "ERROR: no compact artifacts in \${src}" >&2
  exit 1
fi

n=\$(python3 -c "import json; print(len(json.load(open('\${dst}/episode_manifests.json'))))")
echo "Published \${run_id}: \${copied} file(s), \${n} manifest row(s) (from \${src})"
EOF
)

  ssh "${BABEL_LOGIN}" "srun --partition='${BABEL_STAGE_PARTITION}' --cpus-per-task=1 \
    --mem='${BABEL_STAGE_MEM}' --time='${BABEL_STAGE_TIME}' -n1 \
    bash --noprofile --norc -s" <<< "${remote_cmd}"
}

for run_id in "$@"; do
  publish_one "${run_id}"
done

echo "Done. Shared outputs: ${BABEL_SHARED_OUTPUT_ROOT}/"
