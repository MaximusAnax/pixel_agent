#!/usr/bin/env bash
#SBATCH --job-name=gtraj-demo
#SBATCH --partition=general
#SBATCH --gres=gpu:L40S:1
#SBATCH --time=01:30:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=12
#SBATCH --output=%x-%j.out
# End-to-end guided grounded replay of ONE OSWorld task, co-located on one GPU node:
# UGround-V1-7B (grounding) + OSWorld VM (Apptainer+QEMU/KVM, VNC) + replay driver.
# You can watch live over VNC; the agent waits for a GO file before acting.
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
STAGE_DIR="${STAGE_DIR:?set STAGE_DIR=/abs/path/to/goldTrajectories at submit}"
TASK_FILE="${TASK_FILE:-$ASSET_DIR/tasks_human/bb5e4c0d-f964-439c-97b6-bdb9747de3f4.json}"
export ASSET_DIR
export SIF="${SIF:-$ASSET_DIR/osworld-docker.sif}"
export BASE_QCOW2="${BASE_QCOW2:-$ASSET_DIR/vm_data/Ubuntu.qcow2}"
export WORK="${WORK:-$ASSET_DIR/run/$SLURM_JOB_ID}"
export RAM_SIZE="${RAM_SIZE:-8G}"
export CPU_CORES="${CPU_CORES:-4}"
export SRV_PORT="${SRV_PORT:-5000}"
export VNC_DISPLAY="${VNC_DISPLAY:-0}"
UG_PORT="${UG_PORT:-8500}"
VNC_PORT=$((5900 + VNC_DISPLAY))
LOGIN_HOST="${LOGIN_HOST:-login.babel.cs.cmu.edu}"
NODE=$(hostname)
mkdir -p "$WORK/replay"

VM_PID=""; UG_PID=""
cleanup() {
  echo "== teardown =="
  [ -n "$UG_PID" ] && kill "$UG_PID" 2>/dev/null || true
  [ -n "$VM_PID" ] && kill "$VM_PID" 2>/dev/null || true
  pkill -u "$USER" -f "overlay.qcow2" 2>/dev/null || true
}
trap cleanup EXIT

echo "== [1/4] boot VM (VNC on :$VNC_PORT) on $NODE =="
bash "$STAGE_DIR/scripts/launch_vm.sh" > "$WORK/launch.log" 2>&1 &
VM_PID=$!

echo "== [2/4] start UGround server on :$UG_PORT (GPU) =="
"$ASSET_DIR/venv-ground/bin/python" "$STAGE_DIR/scripts/ug_server.py" \
  --model "$ASSET_DIR/models/UGround-V1-7B" --host 127.0.0.1 --port "$UG_PORT" \
  > "$WORK/ug.log" 2>&1 &
UG_PID=$!

echo "== [3/4] wait for VM :$SRV_PORT and UGround :$UG_PORT =="
for _ in $(seq 1 120); do curl -sf -o /dev/null "http://127.0.0.1:$SRV_PORT/screenshot" && break || sleep 5; done
curl -sf -o /dev/null "http://127.0.0.1:$SRV_PORT/screenshot" && echo "  VM ready" || { echo "  VM NOT ready"; exit 1; }
for _ in $(seq 1 120); do curl -sf "http://127.0.0.1:$UG_PORT/health" | grep -q true && break || sleep 5; done
curl -sf "http://127.0.0.1:$UG_PORT/health" | grep -q true && echo "  UGround ready" || { echo "  UGround NOT ready"; tail -20 "$WORK/ug.log"; exit 1; }
# keep the desktop awake
curl -s -X POST "http://127.0.0.1:$SRV_PORT/execute" -H 'Content-Type: application/json' \
  -d '{"command":["python3","-c","import subprocess as s\nfor c in [\"xset s off\",\"xset -dpms\",\"xset s noblank\"]:\n s.run(c,shell=True)"],"shell":false}' >/dev/null 2>&1 || true

cat <<INFO | tee "$WORK/connect.txt"

============================================================
 READY. Watch live, then let the agent go.
 Node: $NODE   VNC: 127.0.0.1:$VNC_PORT
 Tunnel from your laptop:
   ssh -N -L $VNC_PORT:127.0.0.1:$VNC_PORT -J $USER@$LOGIN_HOST $USER@$NODE
 VNC client -> localhost:$VNC_PORT   (macOS: vnc://localhost:$VNC_PORT)

 The agent starts when $WORK/GO appears (auto-starts after 25 min).
============================================================
INFO

echo "== waiting for GO (touch $WORK/GO) =="
for _ in $(seq 1 300); do [ -f "$WORK/GO" ] && break || sleep 5; done

echo "== [4/4] run guided grounded replay =="
export PYTHONPATH="$ASSET_DIR/OSWorld"
set +e
xvfb-run -a "$ASSET_DIR/venv-osworld/bin/python" "$STAGE_DIR/scripts/replay_agent.py" \
  --task-file "$TASK_FILE" --ug-url "http://127.0.0.1:$UG_PORT" \
  --vm-host 127.0.0.1 --vm-port "$SRV_PORT" \
  --stage-dir "$STAGE_DIR" --outdir "$WORK/replay" --settle 25 --step-pause 2.5
RC=$?
set -e
echo "== replay exit: $RC =="
cat "$WORK/replay/manifest.json" 2>/dev/null || true

echo "== VM stays up for review until $WORK/STOP or time limit =="
for _ in $(seq 1 240); do [ -f "$WORK/STOP" ] && break || sleep 15; done
exit $RC
