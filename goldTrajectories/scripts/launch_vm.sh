#!/usr/bin/env bash
# Launch the OSWorld Ubuntu VM under Apptainer + QEMU/KVM on Babel.
#
# Design notes (see docs/spike_plan.md):
#   * The OSWorld docker image (happysixd/osworld-docker) is the stock qemus/qemu
#     runner. Its entry.sh sets up a TAP/bridge + dnsmasq that needs NET_ADMIN,
#     which unprivileged Apptainer does not grant. We therefore BYPASS entry.sh
#     and drive the image's own `qemu-system-x86_64` directly with user-mode
#     (SLIRP) networking + hostfwd. The guest DHCPs to 10.0.2.15 either way, so
#     hostfwd reaches the in-guest OSWorld server on :5000 with no privileges.
#   * The image boots via UEFI (edk2/OVMF) with a virtio-blk disk on a q35
#     machine — mirrored below.
#   * The base qcow2 stays read-only; we boot a disposable qcow2 overlay so a
#     task run never mutates the golden base image.
#
# Usage: launch_vm.sh   (configure via env vars below; all have defaults)
set -Eeuo pipefail

ASSET_DIR="${ASSET_DIR:-/data/group_data/mattlab/raghavg3/osworld_env}"
SIF="${SIF:-$ASSET_DIR/osworld-docker.sif}"
BASE_QCOW2="${BASE_QCOW2:-$ASSET_DIR/vm_data/Ubuntu.qcow2}"
WORK="${WORK:-$ASSET_DIR/run/$SLURM_JOB_ID}"          # per-run scratch (overlay, vars, logs)
RAM_SIZE="${RAM_SIZE:-8G}"
CPU_CORES="${CPU_CORES:-4}"

# Host ports forwarded to the guest (server=5000, chromium=9222, vnc=8006, vlc=8080).
SRV_PORT="${SRV_PORT:-5000}"
CDP_PORT="${CDP_PORT:-9222}"
VNC_PORT="${VNC_PORT:-8006}"
VLC_PORT="${VLC_PORT:-8080}"

# OVMF firmware lives inside the SIF.
OVMF_CODE_IN="${OVMF_CODE_IN:-/usr/share/OVMF/OVMF_CODE_4M.fd}"
OVMF_VARS_IN="${OVMF_VARS_IN:-/usr/share/OVMF/OVMF_VARS_4M.fd}"

log() { echo "[launch_vm $(date +%H:%M:%S)] $*"; }

[[ -f "$SIF" ]] || { echo "SIF not found: $SIF" >&2; exit 1; }
[[ -f "$BASE_QCOW2" ]] || { echo "base qcow2 not found: $BASE_QCOW2" >&2; exit 1; }
[[ -e /dev/kvm ]] || { echo "/dev/kvm not present on $(hostname)" >&2; exit 1; }

mkdir -p "$WORK"
OVERLAY="$WORK/overlay.qcow2"
VARS="$WORK/OVMF_VARS.fd"
SERIAL_LOG="$WORK/serial.log"

# Writable UEFI NVRAM copy (extracted from the SIF).
log "Extracting OVMF vars -> $VARS"
apptainer exec "$SIF" cat "$OVMF_VARS_IN" > "$VARS"

# Disposable overlay on top of the read-only base image.
log "Creating disposable overlay -> $OVERLAY (backing: $BASE_QCOW2)"
apptainer exec "$SIF" qemu-img create -f qcow2 -b "$BASE_QCOW2" -F qcow2 "$OVERLAY" >/dev/null

HOSTFWD="hostfwd=tcp:127.0.0.1:${SRV_PORT}-:5000"
HOSTFWD+=",hostfwd=tcp:127.0.0.1:${CDP_PORT}-:9222"
HOSTFWD+=",hostfwd=tcp:127.0.0.1:${VNC_PORT}-:8006"
HOSTFWD+=",hostfwd=tcp:127.0.0.1:${VLC_PORT}-:8080"

log "Booting VM on $(hostname): srv=$SRV_PORT cdp=$CDP_PORT vnc=$VNC_PORT (serial -> $SERIAL_LOG)"
# NOTE: do NOT `--bind /dev/kvm`. Apptainer already bind-mounts host /dev
# (mount dev = yes), where /dev/kvm is world-rw and works; explicitly re-binding
# the device node breaks access ("Could not access KVM kernel module").
exec apptainer exec --bind "$WORK" --bind "$(dirname "$BASE_QCOW2")" "$SIF" \
  qemu-system-x86_64 \
    -machine q35,accel=kvm,smm=off,graphics=off,vmport=off,dump-guest-core=off,hpet=off \
    -cpu host -smp "$CPU_CORES" -m "$RAM_SIZE" \
    -drive if=pflash,format=raw,unit=0,readonly=on,file="$OVMF_CODE_IN" \
    -drive if=pflash,format=raw,unit=1,file="$VARS" \
    -device virtio-blk-pci,drive=disk0,bootindex=1 \
    -drive id=disk0,if=none,file="$OVERLAY",format=qcow2,cache=unsafe,discard=unmap \
    -netdev user,id=n0,"$HOSTFWD" \
    -device virtio-net-pci,netdev=n0 \
    -object rng-random,id=rng0,filename=/dev/urandom \
    -device virtio-rng-pci,rng=rng0 \
    -vga std -display none \
    -serial file:"$SERIAL_LOG" \
    -monitor none
