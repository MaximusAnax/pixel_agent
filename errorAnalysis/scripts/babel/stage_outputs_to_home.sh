#!/usr/bin/env bash
# Copy compact analysis artifacts from shared group outputs to home mirror.
#
# Run on a compute node (end of analyze_hf_osworld.sbatch), or via srun.

set -euo pipefail

for _babel_env in \
  "${HOME}/cua-failure-analysis/config/babel.env" \
  "${HOME}/.pixel_agent/babel.env"; do
  if [[ -f "${_babel_env}" ]]; then
    # shellcheck disable=SC1090
    source "${_babel_env}"
    break
  fi
done

: "${BABEL_USER:=${USER}}"
: "${BABEL_HOME_DIR:=/home/${BABEL_USER}}"
: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_OUTPUT_ROOT:=${BABEL_GROUP_ROOT}/outputs}"
: "${BABEL_OUTPUT_ROOT:=${BABEL_SHARED_OUTPUT_ROOT}}"
: "${BABEL_OUTPUT_MIRROR:=${BABEL_HOME_DIR}/cua-failure-analysis/data/babel_outputs}"
: "${STAGE_NORMALIZED_TRACES:=0}"

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: $0 <run_id>" >&2
  exit 2
fi

SRC="${BABEL_OUTPUT_ROOT}/${RUN_ID}"
DST="${BABEL_OUTPUT_MIRROR}/${RUN_ID}"

if [[ ! -d "${SRC}" ]]; then
  echo "ERROR: source output dir not found on compute node: ${SRC}" >&2
  exit 1
fi

mkdir -p "${DST}"
copied=0
for file in "${SRC}"/*.json "${SRC}"/*.jsonl "${SRC}"/*.csv "${SRC}"/*.md; do
  [[ -e "${file}" ]] || continue
  cp -a "${file}" "${DST}/"
  copied=$((copied + 1))
done

if [[ "${copied}" -eq 0 ]]; then
  echo "ERROR: no compact artifacts found in ${SRC}" >&2
  exit 1
fi

if [[ ! -f "${DST}/summary.md" ]]; then
  echo "ERROR: staged dir missing summary.md: ${DST}" >&2
  exit 1
fi

if [[ "${STAGE_NORMALIZED_TRACES}" != "0" && -d "${SRC}/normalized_traces" ]]; then
  cp -a "${SRC}/normalized_traces" "${DST}/normalized_traces"
  echo "Staged normalized_traces/ for login sync: ${DST}/normalized_traces"
fi

echo "Staged ${copied} file(s) for login sync: ${DST}"
