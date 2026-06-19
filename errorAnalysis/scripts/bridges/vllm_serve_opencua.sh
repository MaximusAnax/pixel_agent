#!/usr/bin/env bash
# Run vLLM for OpenCUA-7B inside an active Bridges GPU allocation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/../../config/bridges.env" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/../../config/bridges.env"
else
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/../../config/bridges.env.example"
fi

# Bridges: load cluster CUDA before vLLM (fixes libcudart.so.13 missing)
if command -v module &>/dev/null; then
  if module is-avail cuda/12.6.1 2>/dev/null; then
    module load cuda/12.6.1
  elif module is-avail cuda/12.6 2>/dev/null; then
    module load cuda/12.6
  else
    module load cuda 2>/dev/null || true
  fi
fi
if [[ -n "${CUDA_HOME:-}" ]]; then
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
fi

# Prefer dedicated env over py313 (Python 3.13 + vllm 0.23 breaks on Bridges)
if [[ -z "${CONDA_DEFAULT_ENV:-}" ]] || [[ "${CONDA_DEFAULT_ENV}" == "py313" ]]; then
  if command -v conda &>/dev/null; then
    eval "$(conda shell.bash hook)"
    if conda env list | awk '{print $1}' | grep -qx cua-vllm; then
      conda activate cua-vllm
    fi
  fi
fi

export VLLM_NODE
VLLM_NODE="$(hostname)"
export VLLM_PORT="${VLLM_PORT:-8000}"

echo "=== vLLM smoke serve ==="
echo "Node: ${VLLM_NODE}"
echo "Endpoint: http://${VLLM_NODE}:${VLLM_PORT}/v1"
echo "Model: ${VLLM_MODEL}"
echo "Python: $(which python3 2>/dev/null || which python)"
python3 -c "import vllm; print('vllm', vllm.__version__)" 2>/dev/null || {
  echo "ERROR: vllm not importable. Run: bash scripts/bridges/setup_vllm_env.sh"
  exit 1
}
nvidia-smi || true

vllm serve "${VLLM_MODEL}" \
  --trust-remote-code \
  --served-model-name "${VLLM_SERVED_NAME}" \
  --host 0.0.0.0 \
  --port "${VLLM_PORT}"
