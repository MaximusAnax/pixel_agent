#!/bin/bash
#SBATCH -A cis260099p
#SBATCH -p GPU-shared
#SBATCH --gres=gpu:1
#SBATCH -t 24:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=60G
#SBATCH -J cua-vllm
#SBATCH -o logs/vllm-%j.out

set -euo pipefail
mkdir -p logs

module load anaconda3 2>/dev/null || true
# Bridges CUDA 12 — required for vLLM (do not use pip CUDA 13 wheels alone)
if module is-avail cuda/12.6.1 2>/dev/null; then
  module load cuda/12.6.1
else
  module load cuda 2>/dev/null || true
fi
export LD_LIBRARY_PATH="${CUDA_HOME:-}/lib64:${LD_LIBRARY_PATH:-}"

# Use cua-vllm env if present (see scripts/bridges/setup_vllm_env.sh)
eval "$(conda shell.bash hook)" 2>/dev/null || true
conda activate cua-vllm 2>/dev/null || conda activate py313 2>/dev/null || true

export VLLM_NODE
VLLM_NODE="$(hostname)"
export VLLM_PORT=8000
echo "vLLM endpoint: http://${VLLM_NODE}:${VLLM_PORT}/v1" | tee "logs/vllm-endpoint-${SLURM_JOB_ID}.txt"

vllm serve xlangai/OpenCUA-7B \
  --trust-remote-code \
  --served-model-name opencua-7b \
  --host 0.0.0.0 \
  --port "${VLLM_PORT}"
