#!/bin/bash
#SBATCH --job-name=cua-judge
#SBATCH --partition=general
#SBATCH --gres=gpu:L40S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/judge_%j.out
#SBATCH --error=outputs/judge_%j.err

# Local vLLM judge (Qwen2.5-VL-7B). Submit from errorAnalysis/:
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge.sbatch --limit 40  # validate
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge.sbatch              # full (resumes)
# Extra args pass straight through to run_judge.

set -euo pipefail

EA=/data/group_data/mattlab/raghavg3/pixel_agent/errorAnalysis
ENV=/data/group_data/mattlab/raghavg3/envs/cua-judge

# Keep all HF caches (model weights, datasets) on group storage, not home.
export HF_HOME=/data/group_data/mattlab/raghavg3/hf_cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn

source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$ENV"
# Make the in-repo package importable without pip-installing into the GPU env.
export PYTHONPATH="$EA/src:${PYTHONPATH:-}"

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true
echo "Python: $(which python)"

cd "$EA"
python -m cua_failure_analysis.trajectory_judge.run_judge \
    --backend local \
    --failures outputs/failures.jsonl \
    --out outputs/classifications_local_7b.jsonl \
    --model "Qwen/Qwen2.5-VL-7B-Instruct" \
    "$@"
