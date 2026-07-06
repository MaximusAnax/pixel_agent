# Babel HF OSWorld Orchestration

This document describes the Phase 1 workflow for analyzing existing
OSWorld-Verified trajectories from Hugging Face on Babel without downloading raw
trajectory zips to the laptop.

## Architecture

```text
Local pixelAgent repo (git push)
  -> sync_shared_repo.sh pull on Babel compute
  -> shared clone at /data/group_data/mattlab/pixel_agent/pixelAgent
  -> submit Slurm job from errorAnalysis/
  -> HF zips in per-user /data/group_data/mattlab/$USER (or user_data)
  -> compact outputs under /data/group_data/mattlab/pixel_agent/outputs/<run_id>
  -> stage_outputs_to_home.sh mirrors to ~/cua-failure-analysis/data/babel_outputs
  -> local machine syncs JSONL/CSV/MD summaries only
```

## Shared mattlab project root

Abdoul and Raghav share one Babel project tree under **`/data/group_data/mattlab/pixel_agent/`**:

| Path | Purpose |
|---|---|
| `pixelAgent/` | Full git clone (canonical code on Babel) |
| `outputs/` | Shared analysis run artifacts |
| `review_packets/` | HTML trace review packets |
| `review_annotations/` | Multi-annotator `annotations.json` |
| `.venv/` | Shared Python environment |
| `BABEL_SETUP.md` | Init checklist (written by `init_shared_project.sh`) |

**One-time init** (either person, from laptop):

```bash
source config/babel.env
scripts/babel/init_shared_project.sh
```

**Before each submit or packet build:**

```bash
git push   # from pixelAgent repo root
cd errorAnalysis && scripts/babel/sync_shared_repo.sh pull
```

Per-user only: `config/babel.env` secrets on laptop; copy API keys to `~/cua-failure-analysis/config/babel.env` or `~/.pixel_agent/babel.env` on Babel for judge calls.

## Files

| File | Purpose |
|---|---|
| `config/babel.env.example` | Babel login, storage, Slurm, HF cache defaults |
| `config/hf_osworld_packages.yaml` | Curated package inventory for modern models |
| `scripts/babel/init_shared_project.sh` | One-time shared repo + venv setup on mattlab group space |
| `scripts/babel/sync_shared_repo.sh` | `git pull` shared clone on compute |
| `scripts/babel/submit_hf_analysis.sh` | Pull shared repo and submit Slurm job |
| `scripts/babel/analyze_hf_osworld.sbatch` | Remote Slurm job wrapper |
| `scripts/babel/setup_env.sh` | Python environment setup (shared `.venv` or legacy home) |
| `scripts/babel/stage_outputs_to_home.sh` | Copy compact outputs from group storage to home mirror |
| `scripts/babel/sync_outputs.sh` | Pulls compact outputs back locally |
| `scripts/babel/publish_outputs_to_shared.sh` | Copy legacy/home runs → shared `outputs/` (before packet build) |
| `scripts/babel/wait_for_run.sh` | Polls until summary.md exists or Slurm job fails |
| `scripts/hf_osworld_analyze.py` | Remote zip inventory and best-effort analyzer |
| `hermes/SOUL.md` | Hermes operating contract for Phase 1 |

## First-Time Local Setup

From `errorAnalysis`:

```bash
cp config/babel.env.example config/babel.env
```

If your lab later gives you a required Slurm account or QoS, set:

```bash
export BABEL_ACCOUNT=<account>
export BABEL_QOS=<qos>
```

After init, the shared Python environment lives at
`/data/group_data/mattlab/pixel_agent/.venv` (created by `init_shared_project.sh`).

Legacy per-user home layout (`~/cua-failure-analysis/.venv`) is no longer used for
submits when the shared mattlab paths are configured in `babel.env`.

```bash
# One-time shared setup (from laptop):
source config/babel.env
scripts/babel/init_shared_project.sh
```

The first `submit_hf_analysis.sh` run calls `sync_shared_repo.sh pull` and fails fast
if the shared venv is missing — run `init_shared_project.sh` first, or repair with
`scripts/babel/bootstrap_shared_venv.sh` if the env landed under `errorAnalysis/.venv`.
Submits use `${BABEL_SHARED_VENV}/bin/python` on the shared clone.

## Smoke Test

Run from your local machine:

```bash
cd errorAnalysis
git push   # from pixelAgent repo root
scripts/babel/sync_shared_repo.sh pull
scripts/babel/submit_hf_analysis.sh \
  opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip
```

The script prints the run id and the shared output directory:

```text
/data/group_data/mattlab/pixel_agent/outputs/<run_id>
```

After the Slurm job completes:

```bash
scripts/babel/sync_outputs.sh <run_id>
```

Local compact outputs land at:

```text
errorAnalysis/data/babel_outputs/<run_id>
```

## Babel Storage Policy

Babel storage tiers (from the quickstart guide):

- `/home/<andrewID>` — 100GB, mounted on all nodes (login + compute).
- `/data/user_data/<andrewID>` — 500GB, on compute nodes, persistent across jobs.
- `/data/group_data/<lab>` — 8TB lab group space, **compute nodes only, not the
  login node**. Best for large models/datasets. Files are readable/writable by
  the whole lab, so always create and work inside your own subdirectory
  (`mkdir /data/group_data/<lab>/$USER`).
- `/scratch` — node-local SSD/NVMe, auto-expunged; temporary work only.

Use:

- `/data/group_data/mattlab/pixel_agent/pixelAgent` for the **shared git clone** and job code path.
- `/data/group_data/mattlab/pixel_agent/outputs` for **shared analysis outputs** (abdoul + raghav).
- `/data/group_data/mattlab/$USER` (`BABEL_GROUP_DIR`) for per-user HF cache and zips.
- `~/cua-failure-analysis/data/` on home for **login-visible mirrors** only (rsync staging).
- `/scratch` or the configured work root for temporary extraction.

Legacy (pre-shared layout):

- `/home/<user>/cua-failure-analysis` — deprecated as code location; mirrors only.
- `/data/user_data/<user>/cua_failure_analysis/outputs` — migrate old runs to shared outputs manually if needed.

Avoid:

- raw zips or HF caches in `/home/andiongu` (only 100GB);
- full dataset mirrors;
- laptop-local HF downloads;
- listing `/data/group_data` or `/data/user_data` from the login node — these are
  AutoFS/compute-node paths and may appear empty until touched on a compute node.

## Slurm Conventions

Babel uses Slurm. Two patterns matter for this project (per the quickstart guide):

Interactive session on the `debug` partition (no GPU — e.g. inspecting data dirs):

```bash
srun --partition debug --cpus-per-task 2 --mem=32000 --wait=0 -t 02:00:00 -n 1 --pty bash
```

Interactive session with one GPU (the GPU type is required in `--gres`):

```bash
srun --partition debug --cpus-per-task 2 --mem=32000 --wait=0 -t 02:00:00 -n 1 \
  --gres=gpu:L40S:1 --pty bash
```

Non-interactive GPU batch job on the `general` partition:

```bash
sbatch --partition general --cpus-per-task 2 --mem=32000 -t 02:00:00 -n 1 \
  --gres=gpu:L40S:1 ./run.sh
```

`submit_hf_analysis.sh` builds these flags from `config/babel.env`. Phase 1 is
CPU-only (`BABEL_PARTITION=cpu`, `BABEL_GPUS=0`); for a GPU run set
`BABEL_PARTITION=general`, `BABEL_GPUS=1`, and `BABEL_GPU_TYPE` (default `L40S`).

### GPUs and CUDA

- Always specify a GPU **type**: `gpu:L40S:1`, never `gpu:1`. Available types
  include `L40S`, `L40`, `A6000`, `6000Ada`, `A100_40GB`, `A100_80GB`, `H100`.
- `L40S` is the most plentiful; `A100_80GB`/`A100_40GB`/`L40` are faster but
  scarcer (`python3 /opt/cluster_tools/babel_contrib/gpu_allocations.py` shows
  live availability).
- GPU jobs need CUDA: `module load cuda-12.9` (run `module avail` to list). The
  sbatch wrapper loads it automatically when the job has GPUs; for interactive
  GPU work, add `echo "module load cuda-12.9" >> ~/.bash_profile`.

### Out-of-memory errors

An `oom_kill` error means **CPU** memory ran out, not GPU HBM. Raise `--mem`
(`BABEL_MEM`) without adding GPUs. Rule of thumb from the guide: if the GPU has
48GB of HBM, request ~48GB of CPU memory too.

## VS Code / SSH Access

To reach interactive compute-node sessions from VS Code (or plain SSH) without
adding a new host entry per node, configure `~/.ssh/config` as in the guide:

```ssh-config
Host babel
  HostName login.babel.cs.cmu.edu
  User yourandrewID
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking no

Host babel-*
  HostName %h
  User yourandrewID
  IdentityFile ~/.ssh/id_ed25519
  ProxyJump babel
  StrictHostKeyChecking no
```

Then `ssh babel` reaches the login node and `ssh babel-x9-16` (etc.) jumps to a
compute node where your `srun` session is running.

## Package Progression

Start small:

```text
OpenCUA A3B 15-step
OpenCUA 7B 15-step
Kimi K26
Claude Sonnet 4.5 15-step
OpenCUA 7B 50-step
OpenCUA 32B 50-step
Claude Sonnet 4.5 50-step
```

## What The First Analyzer Does

The current analyzer is a remote plumbing and adapter-discovery pass. It:

1. Ensures the selected zip exists on Babel.
2. Inventories zip members.
3. Groups members into candidate episodes.
4. Extracts bounded JSON/text files for a sample of episodes.
5. Best-effort normalizes reasoning/action records.
6. Emits unresolved queues when package-specific mapping is needed.

This is deliberate. The HF repo is zip-based and can have package-specific
internal layouts. The first run tells us where the actual step-level reasoning
and actions live, then we harden the adapter.

## Expected Outputs

```text
run_metadata.json
zip_inventory.json
episode_manifests.json
adapter_gaps.json
failure_labels.jsonl
human_review_queue.jsonl
aggregate_stats.csv
summary.md
```

Read `summary.md` first, then inspect `adapter_gaps.json`.

## Next Calibration Step

Once the package layout is known, add a package-specific adapter that maps:

```text
instruction
step index
screenshot path
reasoning trace
action
coordinates
evaluator result
success/failure
```

into `cua_failure_analysis.trace.schema.TraceStep`.

Then rerun the same Babel workflow and enable the calibrated judge.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `submit_hf_analysis.sh` exits before Slurm | Remote `.venv` missing — run `scripts/babel/setup_env.sh` on Babel. |
| `ModuleNotFoundError: huggingface_hub` in Slurm logs | Same — job ran without the project venv (should not happen after the fail-fast check). |
| Poll runs for hours, job already gone | Job failed without `summary.md`. Use `wait_for_run.sh`; inspect `logs/cua-hf-analysis-<job_id>.err`. |
| `wait_for_run` errors but log says Analysis complete | Outputs live on compute-node `/data/user_data/...` only. Run `sync_outputs.sh` (stages via srun, then rsyncs). |
| `oom_kill` | CPU RAM, not HBM — raise `BABEL_MEM`. |
