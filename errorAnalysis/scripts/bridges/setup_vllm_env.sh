#!/usr/bin/env bash
# Create a Bridges-compatible vLLM conda env (CUDA 12 + pinned vllm).
# Run INSIDE a GPU allocation on v016 (or any GPU node).
#
# Usage:
#   bash scripts/bridges/setup_vllm_env.sh
#   conda activate cua-vllm
#   bash scripts/bridges/vllm_serve_opencua.sh
set -euo pipefail

ENV_NAME="${ENV_NAME:-cua-vllm}"
VLLM_PIN="${VLLM_PIN:-0.12.0}"

echo "=== Loading Bridges CUDA module ==="
# Prefer explicit 12.6; fall back to default cuda module
if module is-avail cuda/12.6.1 2>/dev/null; then
  module load cuda/12.6.1
elif module is-avail cuda/12.6 2>/dev/null; then
  module load cuda/12.6
else
  module load cuda
fi
module list 2>&1 || true

if [[ -n "${CUDA_HOME:-}" ]]; then
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
  export PATH="${CUDA_HOME}/bin:${PATH}"
fi

echo "CUDA_HOME=${CUDA_HOME:-unset}"

if ! command -v conda &>/dev/null; then
  echo "ERROR: conda not found. Run: module load anaconda3"
  exit 1
fi

eval "$(conda shell.bash hook)"

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "Env ${ENV_NAME} exists — activating and reinstalling vllm pin ${VLLM_PIN}"
  conda activate "${ENV_NAME}"
else
  echo "Creating conda env ${ENV_NAME} with Python 3.11"
  conda create -n "${ENV_NAME}" python=3.11 -y
  conda activate "${ENV_NAME}"
fi

pip install --upgrade pip
# Pin vllm: 0.23 pulls CUDA 13 wheels incompatible with Bridges module CUDA 12
pip install "vllm==${VLLM_PIN}" --no-cache-dir

echo ""
echo "=== Verify ==="
python -c "import vllm; print('vllm', vllm.__version__)"
python -c "import vllm._C; print('vllm._C OK')"

echo ""
echo "Done. Activate with: conda activate ${ENV_NAME}"
echo "Then load cuda module in each new session before vllm serve:"
echo "  module load cuda/12.6.1"
echo "  export LD_LIBRARY_PATH=\$CUDA_HOME/lib64:\$LD_LIBRARY_PATH"
