#!/usr/bin/env bash
#SBATCH --job-name=gtraj-dl
#SBATCH --partition=cpu
#SBATCH --time=08:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8
#SBATCH --output=%x-%j.out
# Robust asset download as a SLURM job (survives interactive-session pauses):
# UGround-V1-72B weights + all OSWorld-Human task JSONs. hf_transfer resumes.
set -Eeuo pipefail
ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"

# Download to a FRESH dir: the old UGround-V1-72B/.cache has stuck partials whose
# deletion hangs on NFS (held-open files from cancelled jobs). Data writes are fast;
# only metadata ops on that stuck cache hang, so we avoid it entirely.
MODEL_DIR="${MODEL_DIR:-$ASSET_DIR/models/uground72b}"
echo "== downloading UGround-V1-72B on $(hostname) -> $MODEL_DIR =="
MODEL_DIR="$MODEL_DIR" HF_HUB_ENABLE_HF_TRANSFER=1 "$ASSET_DIR/venv/bin/python" - <<PY
import os
from huggingface_hub import snapshot_download
p = snapshot_download(
    "osunlp/UGround-V1-72B",
    local_dir=os.environ["MODEL_DIR"],
    allow_patterns=["*.safetensors","*.json","*.txt","*.model","tokenizer*","merges*","vocab*"],
    max_workers=8,
)
print("MODEL DONE", p)
PY

echo "== downloading remaining OSWorld-Human task JSONs =="
cd "$ASSET_DIR/tasks_human"
n=0
while IFS= read -r ai; do
  uuid="${ai#*/}"; [ -f "$uuid.json" ] && continue
  curl -sf "https://raw.githubusercontent.com/WukLab/osworld-human/main/${ai}.json" -o "$uuid.json" && n=$((n+1))
done < "$ASSET_DIR/run/all_tasks.txt"
echo "JSONS: downloaded $n new; total $(ls *.json | wc -l)"

echo "== ASSETS READY: 72B shards=$(ls "$MODEL_DIR"/*.safetensors 2>/dev/null | wc -l) in $MODEL_DIR =="
