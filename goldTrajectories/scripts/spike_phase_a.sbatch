#!/usr/bin/env bash
#SBATCH --job-name=gtraj-spike-a
#SBATCH --partition=cpu
#SBATCH --time=00:30:00
#SBATCH --mem=12G
#SBATCH --cpus-per-task=6
#SBATCH --output=%x-%j.out
# Phase-A environment feasibility spike: boot the OSWorld VM under Apptainer+QEMU/KVM
# and prove a screenshot -> action -> screenshot round-trip over the guest HTTP server.
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
STAGE_DIR="${STAGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export ASSET_DIR
export SIF="${SIF:-$ASSET_DIR/osworld-docker.sif}"
export BASE_QCOW2="${BASE_QCOW2:-$ASSET_DIR/vm_data/Ubuntu.qcow2}"
export WORK="${WORK:-$ASSET_DIR/run/$SLURM_JOB_ID}"
export RAM_SIZE="${RAM_SIZE:-8G}"
export CPU_CORES="${CPU_CORES:-4}"
export SRV_PORT="${SRV_PORT:-5000}"
VENV_PY="${VENV_PY:-$ASSET_DIR/venv/bin/python}"

echo "== node: $(hostname) | job: $SLURM_JOB_ID =="
echo "== /dev/kvm: $(ls -l /dev/kvm 2>&1) =="
mkdir -p "$WORK/phase_a"

# 1) Boot the VM in the background.
echo "== launching VM =="
bash "$STAGE_DIR/scripts/launch_vm.sh" > "$WORK/launch.log" 2>&1 &
QEMU_PID=$!
echo "launch_vm pid: $QEMU_PID"

cleanup() {
  echo "== teardown: killing VM ($QEMU_PID) =="
  kill "$QEMU_PID" 2>/dev/null || true
  # QEMU runs inside apptainer; make sure it is gone.
  pkill -u "$USER" -f "qemu-system-x86_64.*$SLURM_JOB_ID" 2>/dev/null || true
  pkill -u "$USER" -f "overlay.qcow2" 2>/dev/null || true
}
trap cleanup EXIT

# 2) Drive the spike (waits for the guest server to come up).
echo "== running phase-a driver =="
set +e
"$VENV_PY" "$STAGE_DIR/scripts/spike_phase_a.py" \
  --host 127.0.0.1 --port "$SRV_PORT" \
  --outdir "$WORK/phase_a" --boot-timeout 600
RC=$?
set -e

echo "== phase-a exit code: $RC =="
echo "== serial tail =="
tail -30 "$WORK/serial.log" 2>/dev/null || true
echo "== artifacts in $WORK/phase_a =="
ls -l "$WORK/phase_a" 2>/dev/null || true
exit $RC
