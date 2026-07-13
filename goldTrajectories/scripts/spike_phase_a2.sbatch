#!/usr/bin/env bash
#SBATCH --job-name=gtraj-spike-a2
#SBATCH --partition=cpu
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=6
#SBATCH --output=%x-%j.out
# Phase-A2: boot the VM, then diagnose + fix the black-screen and re-capture.
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
VENV_PY="${VENV_PY:-$ASSET_DIR/venv/bin/python}"

echo "== node: $(hostname) | job: $SLURM_JOB_ID =="
mkdir -p "$WORK/phase_a2"

bash "$STAGE_DIR/scripts/launch_vm.sh" > "$WORK/launch.log" 2>&1 &
QEMU_PID=$!
cleanup() { kill "$QEMU_PID" 2>/dev/null || true; pkill -u "$USER" -f "overlay.qcow2" 2>/dev/null || true; }
trap cleanup EXIT

set +e
"$VENV_PY" "$STAGE_DIR/scripts/spike_phase_a2.py" \
  --host 127.0.0.1 --port "$SRV_PORT" \
  --outdir "$WORK/phase_a2" --boot-timeout 600 --settle 45
RC=$?
set -e
echo "== a2 exit: $RC =="
ls -l "$WORK/phase_a2" 2>/dev/null || true
exit $RC
