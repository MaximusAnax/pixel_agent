#!/bin/bash
#SBATCH --job-name=judge-a3b-7b
#SBATCH --partition=general
#SBATCH --gres=gpu:L40S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/judge_a3b_7b_%j.out
#SBATCH --error=outputs/judge_a3b_7b_%j.err

# 7B local vLLM judge over the OpenCUA-A3B failed trajectories. From errorAnalysis/:
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge_a3b_7b.sbatch --limit 40
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge_a3b_7b.sbatch          # full
# Extra args pass through to run_judge.

set -euo pipefail
EA=/data/group_data/mattlab/raghavg3/pixel_agent/errorAnalysis
ENV=/data/group_data/mattlab/raghavg3/envs/cua-judge

export HF_HOME=/data/group_data/mattlab/raghavg3/hf_cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn

source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$ENV"
export PYTHONPATH="$EA/src:${PYTHONPATH:-}"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true

cd "$EA"
python -m cua_failure_analysis.trajectory_judge.run_judge \
    --backend local \
    --failures outputs/failures_a3b.jsonl \
    --out outputs/classifications_a3b_local_7b.jsonl \
    --model "Qwen/Qwen2.5-VL-7B-Instruct" \
    "$@"
