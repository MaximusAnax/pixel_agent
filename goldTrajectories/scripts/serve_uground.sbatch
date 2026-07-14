#!/usr/bin/env bash
#SBATCH --job-name=uground-72b
#SBATCH --partition=general
#SBATCH --qos=normal
#SBATCH --gres=gpu:A100_80GB:2
#SBATCH --time=12:00:00
#SBATCH --mem=220G
#SBATCH --cpus-per-task=8
#SBATCH --output=%x-%j.out
# Persistent UGround-V1-72B grounding server on 2x A100-80GB (device_map=auto).
# Writes its <node>:<port> endpoint so batch runners on other nodes can reach it.
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
STAGE_DIR="${STAGE_DIR:?set STAGE_DIR at submit}"
# Serve from the COMPLETE weights dir. The old `models/UGround-V1-72B` was an
# aborted download (no safetensors, NFS-zombie .cache); it was quarantined and
# deleted 2026-07-14 once the zombie handles cleared. `models/uground72b` is the
# clean, full copy fetched by download_assets.sbatch (31 shards + index). Never
# point MODEL at the old name again.
MODEL="${MODEL:-$ASSET_DIR/models/uground72b}"
PORT="${UG_PORT:-8500}"
ENDPOINT_FILE="${ENDPOINT_FILE:-$ASSET_DIR/run/uground_endpoint.txt}"

# Fail fast on an incomplete model dir instead of writing an endpoint and letting
# batch runners burn their 30-min /health wait on a server that can never load.
shards=$(ls "$MODEL"/*.safetensors 2>/dev/null | wc -l)
if [ ! -f "$MODEL/model.safetensors.index.json" ] || [ "$shards" -lt 1 ]; then
  echo "FATAL: $MODEL is not a complete model (index missing or 0 safetensors=$shards)." >&2
  echo "       Run scripts/download_assets.sbatch first." >&2
  exit 1
fi

NODE=$(hostname)
echo "== UGround-72B server on $NODE:$PORT (GPUs: $CUDA_VISIBLE_DEVICES; model=$MODEL, shards=$shards) =="
nvidia-smi -L 2>&1 | head -2
mkdir -p "$(dirname "$ENDPOINT_FILE")"
echo "${NODE}:${PORT}" > "$ENDPOINT_FILE"
echo "endpoint written: $(cat "$ENDPOINT_FILE")"

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
exec "$ASSET_DIR/venv-ground/bin/python" "$STAGE_DIR/scripts/ug_server.py" \
  --model "$MODEL" --host 0.0.0.0 --port "$PORT" --device-map auto
