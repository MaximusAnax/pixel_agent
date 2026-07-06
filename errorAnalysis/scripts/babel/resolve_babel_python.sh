#!/usr/bin/env bash
# Resolve the Babel Python interpreter for shared mattlab jobs.
# Source from other scripts:  source scripts/babel/resolve_babel_python.sh
#
# Sets BABEL_PYTHON_BIN. Exits 1 with a helpful message if none found.

: "${BABEL_GROUP_ROOT:=/data/group_data/mattlab/pixel_agent}"
: "${BABEL_SHARED_REPO:=${BABEL_GROUP_ROOT}/pixelAgent}"
: "${BABEL_SHARED_ERROR_ANALYSIS:=${BABEL_SHARED_REPO}/errorAnalysis}"
: "${BABEL_SHARED_VENV:=${BABEL_GROUP_ROOT}/.venv}"

_babel_python_candidates=(
  "${BABEL_SHARED_VENV}/bin/python"
  "${BABEL_SHARED_ERROR_ANALYSIS}/.venv/bin/python"
)

BABEL_PYTHON_BIN=""
for candidate in "${_babel_python_candidates[@]}"; do
  if [[ -x "${candidate}" ]]; then
    BABEL_PYTHON_BIN="${candidate}"
    break
  fi
done

if [[ -z "${BABEL_PYTHON_BIN}" ]]; then
  echo "ERROR: No Babel Python env found. Tried:" >&2
  for candidate in "${_babel_python_candidates[@]}"; do
    echo "  - ${candidate}" >&2
  done
  echo "Fix: scripts/babel/bootstrap_shared_venv.sh" >&2
  exit 1
fi
