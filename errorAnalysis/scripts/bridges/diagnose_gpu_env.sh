#!/usr/bin/env bash
# Diagnose CUDA / vLLM environment on a Bridges GPU node.
set -euo pipefail

echo "=== Host ==="
hostname
echo ""

echo "=== GPU ==="
nvidia-smi || echo "nvidia-smi failed"
echo ""

echo "=== Modules (cuda) ==="
module avail cuda 2>&1 | head -20 || true
echo ""

echo "=== Loaded modules ==="
module list 2>&1 || true
echo ""

echo "=== Python ==="
which python3 || true
python3 --version 2>/dev/null || true
echo ""

echo "=== vLLM ==="
python3 -c "import vllm; print('vllm', vllm.__version__)" 2>&1 || echo "vllm import failed"
echo ""

echo "=== libcudart search ==="
for d in "${CUDA_HOME:-/usr/local/cuda}/lib64" \
         "${CONDA_PREFIX:-}/lib" \
         /usr/lib64 /lib64; do
  if [[ -d "$d" ]]; then
    found=$(find "$d" -maxdepth 1 -name 'libcudart.so*' 2>/dev/null | head -3)
    if [[ -n "$found" ]]; then
      echo "$d:"
      echo "$found"
    fi
  fi
done
echo ""

echo "=== LD_LIBRARY_PATH (first 500 chars) ==="
echo "${LD_LIBRARY_PATH:-unset}" | cut -c1-500
