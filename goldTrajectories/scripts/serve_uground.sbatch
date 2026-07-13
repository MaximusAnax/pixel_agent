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
MODEL="${MODEL:-$ASSET_DIR/models/UGround-V1-72B}"
PORT="${UG_PORT:-8500}"
ENDPOINT_FILE="${ENDPOINT_FILE:-$ASSET_DIR/run/uground_endpoint.txt}"

NODE=$(hostname)
echo "== UGround-72B server on $NODE:$PORT (GPUs: $CUDA_VISIBLE_DEVICES) =="
nvidia-smi -L 2>&1 | head -2
mkdir -p "$(dirname "$ENDPOINT_FILE")"
echo "${NODE}:${PORT}" > "$ENDPOINT_FILE"
echo "endpoint written: $(cat "$ENDPOINT_FILE")"

exec "$ASSET_DIR/venv-ground/bin/python" "$STAGE_DIR/scripts/ug_server.py" \
  --model "$MODEL" --host 0.0.0.0 --port "$PORT" --device-map auto
