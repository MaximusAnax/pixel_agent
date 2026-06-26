#!/usr/bin/env bash
# Copy compact analysis artifacts from compute-node storage to home, where the
# login node and local rsync can reach them.
#
# Run on a compute node (e.g. at the end of analyze_hf_osworld.sbatch), or via:
#   ssh babel "srun --partition=debug ... bash --noprofile --norc \
#     /home/andiongu/cua-failure-analysis/scripts/babel/stage_outputs_to_home.sh <run_id>"

set -euo pipefail

if [[ -f "${HOME}/cua-failure-analysis/config/babel.env" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/cua-failure-analysis/config/babel.env"
fi

: "${BABEL_USER:=andiongu}"
: "${BABEL_PROJECT_DIR:=/home/${BABEL_USER}/cua-failure-analysis}"
: "${BABEL_OUTPUT_ROOT:=/data/user_data/${BABEL_USER}/cua_failure_analysis/outputs}"
: "${BABEL_STAGING_ROOT:=${BABEL_PROJECT_DIR}/data/babel_outputs}"
# Set STAGE_NORMALIZED_TRACES=1 to also copy the per-episode normalized_traces/
# tree (bounded by --phase/--failed-only) for human gold labeling.
: "${STAGE_NORMALIZED_TRACES:=0}"

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: $0 <run_id>" >&2
  exit 2
fi

SRC="${BABEL_OUTPUT_ROOT}/${RUN_ID}"
DST="${BABEL_STAGING_ROOT}/${RUN_ID}"

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
