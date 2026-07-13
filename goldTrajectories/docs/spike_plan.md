# Environment feasibility spike — OSWorld on Babel via Apptainer + QEMU/KVM

**Goal (first step, per Raghav):** prove that one OSWorld task can run live on
Babel — reset → execute an action → capture a screenshot → run the evaluator —
*without Docker, without AWS, without API credits*. This de-risks the whole
gold-trajectory idea, whose only hard dependency is a live OSWorld environment.

## Why this is the crux

`goldTrajectories/` generates **reference ("gold") trajectories**: an agent that
only has to *ground* (not plan) replays the human action sequence from
**OSWorld-Human** on each task, and we keep the runs the OSWorld evaluator marks
correct. The grounding model (UGround-V1-7B) is easy on a 48 GB GPU. The genuinely
uncertain part is standing up the OSWorld VM on a shared SLURM cluster with no
Docker and no root — so we spike that first.

## Cluster facts (verified 2026-07-12)

- **Babel** has `/dev/kvm` present and world-accessible (`crw-rw-rw-`) on the
  login node *and* on compute nodes (confirmed on `babel-m5-32`). Nested virt is
  **not** disabled — this reverses the pessimism in
  `errorAnalysis/docs/osworld_vm_strategy.md`.
- `apptainer` 1.4.0 is installed; **no** Docker / Podman / system QEMU.
- Plenty of 48 GB GPUs (L40S/A6000/L40/6000Ada), plus A100/H100/H200.
- Group space `/data/group_data/mattlab/raghavg3` has ~4.5 TB free.

## How OSWorld's environment actually works (reverse-engineered)

- OSWorld's `docker` provider runs `happysixd/osworld-docker`, a thin
  **qemus/qemu-docker** runner (78 MB SIF). It does **not** bake in the disk; it
  bind-mounts a host `System.qcow2` → `/System.qcow2` and boots it with
  `qemu-system-x86_64`, using `/dev/kvm` when present.
- The Ubuntu disk is a public HF dataset:
  `https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip`
  (~12.3 GB zip).
- Boot recipe extracted from the image: machine **q35**, **UEFI/OVMF**
  (`OVMF_CODE_4M.fd` + writable `OVMF_VARS_4M.fd`, both shipped in the SIF), boot
  disk on **virtio-blk** (`/dev/vda`).
- Guest exposes an HTTP control server on **:5000** (`GET /screenshot`,
  `GET /accessibility`, `POST /execute`, `POST /run_python`, …), plus 8006 (web
  VNC), 9222 (Chrome CDP), 8080 (VLC). `DesktopEnv` drives everything over :5000.

## The Apptainer adaptation (our approach)

The image's `entry.sh` builds a TAP/bridge + dnsmasq that needs **NET_ADMIN**,
which unprivileged Apptainer does not grant. Instead we **bypass entry.sh** and
run the image's own `qemu-system-x86_64` directly with **user-mode (SLIRP)
networking + hostfwd**:

- The guest DHCPs to `10.0.2.15` under SLIRP exactly as it would under the
  bridge, so `hostfwd tcp:127.0.0.1:5000-:5000` reaches the in-guest server with
  **zero privileges** — no NET_ADMIN, no bridge, no CNI.
- The read-only base qcow2 is never mutated: we boot a disposable
  `qemu-img create -b Ubuntu.qcow2` **overlay**, plus a writable OVMF VARS copy.

Implemented in `scripts/launch_vm.sh`.

## Spike phases

- **Phase A — raw round-trip (deps: `requests` only).** `scripts/spike_phase_a.py`
  waits for `:5000`, takes a screenshot, executes a pyautogui action via
  `/execute`, screenshots again. If both PNGs come back, **the environment is
  viable**. Runner: `scripts/spike_phase_a.sbatch` (or run in-allocation on a
  KVM node).
- **Phase B — full task via `DesktopEnv` (deps: targeted subset).** Add a small
  `manual` provider (no-op start/stop, returns `localhost:5000:9222:8006:8080`)
  so `DesktopEnv.reset(task_config)` + `.evaluate()` run on one real OSWorld task
  and return a pass/fail from the task's own checker.

## Assets (outside the repo — large, git-ignored)

Everything heavy lives in `/data/group_data/mattlab/raghavg3/osworld_env/`:
`osworld-docker.sif`, `vm_data/Ubuntu.qcow2`, `OSWorld/` clone, `venv/`, and
per-run scratch under `run/`. The repo holds only scripts, config, and docs.

## Status / findings

_Living section — updated as the spike runs._

- [x] Apptainer pull of `happysixd/osworld-docker` → 78 MB SIF.
- [x] OSWorld driver code cloned; boot recipe + HTTP API extracted.
- [x] `/dev/kvm` + KVM-accel QEMU confirmed available under Apptainer on a node.
- [ ] Ubuntu.qcow2 downloaded + unzipped (~12.3 GB zip).
- [ ] Phase A: VM boots under SLIRP and serves `/screenshot`.
- [ ] Phase B: one task reset + evaluate returns a verdict.
