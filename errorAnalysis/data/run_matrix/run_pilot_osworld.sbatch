#!/bin/bash
#SBATCH -A cis260099p
#SBATCH -p RM-shared
#SBATCH -t 8:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -J osworld-pilot
#SBATCH -o logs/osworld-pilot-%A_%a.out

# Array size: 180 — adjust % array spec after splitting batches
# Requires OSWorld installed and VLLM_BASE_URL set to Bridges GPU node

MATRIX="/Users/Productivity/Documents/School/Research/errorAnalysis/data/run_matrix/pilot_matrix.json"
echo "Run matrix: $MATRIX"
echo "Set OPENAI_BASE_URL and invoke OSWorld per docs/vllm_runbook.md"
