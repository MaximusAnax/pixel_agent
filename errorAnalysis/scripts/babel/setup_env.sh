#!/usr/bin/env bash
# Bootstrap the lightweight Python environment on Babel.
#
# Default: venv in BABEL_PROJECT_DIR/.venv (legacy home layout).
# Shared layout: set BABEL_VENV_PATH to BABEL_SHARED_VENV before running.
#
#   cd /data/group_data/mattlab/pixel_agent/pixelAgent/errorAnalysis
#   BABEL_VENV_PATH=/data/group_data/mattlab/pixel_agent/.venv scripts/babel/setup_env.sh

set -euo pipefail

: "${BABEL_USER:=andiongu}"
: "${BABEL_PROJECT_DIR:=/home/${BABEL_USER}/cua-failure-analysis}"
: "${BABEL_VENV_PATH:=${BABEL_PROJECT_DIR}/.venv}"

cd "${BABEL_PROJECT_DIR}"

PYTHON_BIN_BOOT="${PYTHON_BIN_BOOT:-python3.12}"
if ! command -v "${PYTHON_BIN_BOOT}" >/dev/null 2>&1; then
  PYTHON_BIN_BOOT="python3"
fi

if [[ ! -d "${BABEL_VENV_PATH}" ]]; then
  "${PYTHON_BIN_BOOT}" -m venv "${BABEL_VENV_PATH}"
fi

"${BABEL_VENV_PATH}/bin/python" -m pip install --upgrade pip
"${BABEL_VENV_PATH}/bin/python" -m pip install -r requirements.txt
"${BABEL_VENV_PATH}/bin/python" -m pip install -e ".[dev]"

echo "Babel Python env ready: ${BABEL_VENV_PATH}/bin/python"
