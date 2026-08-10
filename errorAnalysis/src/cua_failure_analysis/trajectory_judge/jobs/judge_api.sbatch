#!/bin/bash
#SBATCH --job-name=cua-judge-api
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=outputs/judge_api_%j.out
#SBATCH --error=outputs/judge_api_%j.err

# Claude API whole-trajectory judge — no GPU (the model runs at Anthropic; this
# job only reads screenshots off group storage and makes HTTPS calls).
#
#   sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge_api.sbatch \
#       --failures /path/to/failures.jsonl --api-out /path/to/classifications_api.jsonl \
#       --limit 20                                     # validate first
#   ... then re-run without --limit for the full set (runs resume: UIDs already
#   present in the output file are skipped).
# Extra args pass straight through to run_judge.
#
# Screenshot paths inside outputs/failures.jsonl (the 7B + Sonnet-4.5 set) are
# RELATIVE (../data/trajs/...), so this job runs from $TRAJ/src exactly like the
# original local-judge jobs did. failures_a3b.jsonl uses absolute paths and is
# CWD-independent.

set -euo pipefail

EA=/data/group_data/mattlab/raghavg3/pixel_agent/errorAnalysis
TRAJ=/data/group_data/mattlab/raghavg3/osworld_traj_analysis
ENV=/data/group_data/mattlab/raghavg3/envs/cua-judge

# Per-user secret, never in git. Must define ANTHROPIC_API_KEY.
for f in ~/.pixel_agent/anthropic.env ~/.pixel_agent/babel.env; do
    [ -f "$f" ] && source "$f"
done
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is not set (put it in ~/.pixel_agent/anthropic.env)}"
export ANTHROPIC_API_KEY

source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$ENV"
# Make the in-repo package importable without pip-installing into the env.
export PYTHONPATH="$EA/src:${PYTHONPATH:-}"
export TOKENIZERS_PARALLELISM=false

echo "Python: $(which python)"
cd "$TRAJ/src"
python -m cua_failure_analysis.trajectory_judge.run_judge \
    --backend api \
    --failures "$TRAJ/outputs/failures.jsonl" \
    --api-out "$TRAJ/outputs/classifications_api.jsonl" \
    "$@"
