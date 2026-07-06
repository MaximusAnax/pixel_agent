#!/bin/bash
#SBATCH --job-name=cua-judge32b
#SBATCH --partition=general
#SBATCH --gres=gpu:L40S:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=06:00:00
#SBATCH --output=outputs/judge32b_%j.out
#SBATCH --error=outputs/judge32b_%j.err

# Reliability cross-check: re-judge with Qwen2.5-VL-32B (tensor-parallel over 2 GPUs),
# to a SEPARATE output so the 7B results are untouched. Submit from errorAnalysis/:
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge_32b.sbatch --limit 100
# Extra args pass through to run_judge.

set -euo pipefail
EA=/data/group_data/mattlab/raghavg3/pixel_agent/errorAnalysis
ENV=/data/group_data/mattlab/raghavg3/envs/cua-judge

export HF_HOME=/data/group_data/mattlab/raghavg3/hf_cache
export HF_XET_HIGH_PERFORMANCE=1
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn

source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$ENV"
export PYTHONPATH="$EA/src:${PYTHONPATH:-}"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true

cd "$EA"
python -m cua_failure_analysis.trajectory_judge.run_judge \
    --backend local \
    --failures outputs/failures.jsonl \
    --out outputs/classifications_local_32b.jsonl \
    --model "Qwen/Qwen2.5-VL-32B-Instruct" \
    --tensor-parallel-size 2 \
    --gpu-mem-frac 0.92 \
    --chunk 24 \
    "$@"
