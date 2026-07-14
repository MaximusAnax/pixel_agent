#!/usr/bin/env bash
#SBATCH --job-name=gtraj-batch
#SBATCH --partition=cpu
#SBATCH --time=12:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=6
#SBATCH --output=%x-%A_%a.out
# One array shard: for each task in this shard, boot a fresh OSWorld VM, run the
# OSWorld-Human guided grounded replay against the shared remote UGround server,
# evaluate, write a gold trace, tear down. A task is gold iff the evaluator passes.
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
STAGE_DIR="${STAGE_DIR:?set STAGE_DIR at submit}"
TASK_LIST="${TASK_LIST:-$ASSET_DIR/run/all_tasks.txt}"
GOLD_ROOT="${GOLD_ROOT:-$ASSET_DIR/gold}"
ENDPOINT_FILE="${ENDPOINT_FILE:-$ASSET_DIR/run/uground_endpoint.txt}"
K="${NSHARDS:?set NSHARDS at submit (must match --array size)}"
SHARD="${SLURM_ARRAY_TASK_ID:-0}"

# Per-shard host ports so co-located shards don't collide (guest is always :5000).
export SRV_PORT=$((5000 + SHARD * 6))
export CDP_PORT=$((9222 + SHARD * 6))
export VNC_PORT=$((8006 + SHARD * 6))
export VLC_PORT=$((8080 + SHARD * 6))
export SIF="$ASSET_DIR/osworld-docker.sif"
export BASE_QCOW2="$ASSET_DIR/vm_data/Ubuntu.qcow2"
export RAM_SIZE=8G CPU_CORES=4
export PYTHONPATH="$ASSET_DIR/OSWorld"

echo "== shard $SHARD/$K on $(hostname); srv_port=$SRV_PORT =="

# Wait for the grounding server endpoint + health.
for _ in $(seq 1 120); do [ -f "$ENDPOINT_FILE" ] && break; sleep 10; done
UG_URL="http://$(cat "$ENDPOINT_FILE")"
echo "grounding server: $UG_URL"
for _ in $(seq 1 120); do curl -sf "$UG_URL/health" | grep -q true && break; sleep 15; done
curl -sf "$UG_URL/health" | grep -q true || { echo "grounding server not healthy"; exit 1; }

run_one() {
  local uuid="$1" TASK_FILE="$2" OUT="$GOLD_ROOT/$uuid"
  # Skip only verified-gold results; failed runs retry on the next batch.
  [ -f "$OUT/manifest.json" ] && grep -q '"success": true' "$OUT/manifest.json" \
    && { echo "skip $uuid (already gold)"; return; }
  export WORK="$ASSET_DIR/run/batch/${SLURM_ARRAY_JOB_ID}_${SHARD}/$uuid"
  mkdir -p "$WORK" "$OUT"
  bash "$STAGE_DIR/scripts/launch_vm.sh" > "$WORK/launch.log" 2>&1 &
  local VM_PID=$! ok=0
  for _ in $(seq 1 72); do curl -sf -o /dev/null "http://127.0.0.1:$SRV_PORT/screenshot" && { ok=1; break; }; sleep 5; done
  if [ "$ok" = 1 ]; then
    timeout "${REPLAY_TIMEOUT:-420}" xvfb-run -a "$ASSET_DIR/venv-osworld/bin/python" "$STAGE_DIR/scripts/replay_agent.py" \
      --task-file "$TASK_FILE" --ug-url "$UG_URL" --vm-host 127.0.0.1 --vm-port "$SRV_PORT" \
      --stage-dir "$STAGE_DIR" --outdir "$OUT" --settle 18 --step-pause 2.0 \
      > "$OUT/replay.log" 2>&1 || echo "replay error/timeout: $uuid"
  else
    echo "VM-not-ready" > "$OUT/vm_fail.txt"
  fi
  kill "$VM_PID" 2>/dev/null || true
  pkill -u "$USER" -f "$WORK/overlay.qcow2" 2>/dev/null || true
  sleep 3
  echo "done $uuid: $(cat "$OUT/manifest.json" 2>/dev/null | tr -d '\n' | grep -oE '"success": (true|false)' || echo 'no-manifest')"
}

lineno=0
while IFS= read -r app_id; do
  [ -z "$app_id" ] && continue
  if (( lineno % K == SHARD )); then
    uuid="${app_id#*/}"
    run_one "$uuid" "$ASSET_DIR/tasks_human/${uuid}.json"
  fi
  lineno=$((lineno + 1))
done < "$TASK_LIST"
echo "== shard $SHARD complete =="
