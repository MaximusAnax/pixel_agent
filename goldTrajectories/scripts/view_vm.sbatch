#!/usr/bin/env bash
#SBATCH --job-name=gtraj-view
#SBATCH --partition=cpu
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=6
#SBATCH --output=%x-%j.out
# Boot the OSWorld VM with a live VNC display so you can watch the desktop render.
# Connect from your laptop with an SSH tunnel to this compute node (printed below).
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
STAGE_DIR="${STAGE_DIR:?set STAGE_DIR=/abs/path/to/goldTrajectories at submit}"
export ASSET_DIR
export SIF="${SIF:-$ASSET_DIR/osworld-docker.sif}"
export BASE_QCOW2="${BASE_QCOW2:-$ASSET_DIR/vm_data/Ubuntu.qcow2}"
export WORK="${WORK:-$ASSET_DIR/run/$SLURM_JOB_ID}"
export RAM_SIZE="${RAM_SIZE:-8G}"
export CPU_CORES="${CPU_CORES:-4}"
export SRV_PORT="${SRV_PORT:-5000}"
export VNC_DISPLAY="${VNC_DISPLAY:-0}"          # QEMU VNC on 127.0.0.1:$((5900+N))
VNC_PORT=$((5900 + VNC_DISPLAY))
LOGIN_HOST="${LOGIN_HOST:-login.babel.cs.cmu.edu}"

mkdir -p "$WORK"
bash "$STAGE_DIR/scripts/launch_vm.sh" > "$WORK/launch.log" 2>&1 &
QEMU_PID=$!
trap 'kill "$QEMU_PID" 2>/dev/null || true; pkill -u "$USER" -f "overlay.qcow2" 2>/dev/null || true' EXIT

echo "== booting VM on $(hostname); waiting for guest server on :$SRV_PORT =="
for _ in $(seq 1 120); do
  curl -sf -o /dev/null "http://127.0.0.1:$SRV_PORT/screenshot" && break || sleep 5
done
sleep 20   # let GNOME finish painting

# Keep the screen awake while you watch.
curl -s -X POST "http://127.0.0.1:$SRV_PORT/execute" -H 'Content-Type: application/json' \
  -d '{"command":["python3","-c","import subprocess as s\nfor c in [\"xset s off\",\"xset -dpms\",\"xset s noblank\"]:\n s.run(c,shell=True)"],"shell":false}' >/dev/null 2>&1 || true

NODE=$(hostname)
cat <<INFO | tee "$WORK/connect.txt"

============================================================
 LIVE OSWorld desktop is up on compute node: $NODE
 VNC server: 127.0.0.1:$VNC_PORT  (on that node)

 From your laptop, open an SSH tunnel:
   ssh -N -L $VNC_PORT:127.0.0.1:$VNC_PORT -J $USER@$LOGIN_HOST $USER@$NODE

 Then point a VNC client at:
   localhost:$VNC_PORT
 (macOS: Finder > Go > Connect to Server > vnc://localhost:$VNC_PORT)

 Session ends at the SLURM time limit (1h) or when cancelled:
   scancel $SLURM_JOB_ID
============================================================
INFO

echo "== VM running; holding allocation until time limit or scancel =="
wait "$QEMU_PID"
