#!/usr/bin/env bash
# Bootstrap the lightweight Python environment on Babel.
#
# Run on Babel after the repo has been synced:
#   cd /home/andiongu/cua-failure-analysis
#   scripts/babel/setup_env.sh

set -euo pipefail

: "${BABEL_USER:=andiongu}"
: "${BABEL_PROJECT_DIR:=/home/${BABEL_USER}/cua-failure-analysis}"

cd "${BABEL_PROJECT_DIR}"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Babel Python env ready: ${BABEL_PROJECT_DIR}/.venv/bin/python"
