# Babel HF OSWorld Orchestration

This document describes the Phase 1 workflow for analyzing existing
OSWorld-Verified trajectories from Hugging Face on Babel without downloading raw
trajectory zips to the laptop.

## Architecture

```text
Local pixelAgent repo
  -> rsync code/config to Babel /home/andiongu/cua-failure-analysis
  -> submit Slurm job
  -> Babel checks /data/datasets and /data/user_data/andiongu
  -> selected HF zip is read or downloaded remotely
  -> job extracts bounded samples into /scratch or /data/user_data work dir
  -> compact outputs are written under /data/user_data/andiongu
  -> local machine syncs JSONL/CSV/MD summaries only
```

## Files

| File | Purpose |
|---|---|
| `config/babel.env.example` | Babel login, storage, Slurm, HF cache defaults |
| `config/hf_osworld_packages.yaml` | Curated package inventory for modern models |
| `scripts/babel/submit_hf_analysis.sh` | Local helper that syncs code and submits Slurm |
| `scripts/babel/analyze_hf_osworld.sbatch` | Remote Slurm job wrapper |
| `scripts/babel/setup_env.sh` | One-time Python environment setup on Babel |
| `scripts/babel/sync_outputs.sh` | Pulls compact outputs back locally |
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

After the first sync, create the remote Python environment:

```bash
ssh andiongu@login.babel.cs.cmu.edu
cd /home/andiongu/cua-failure-analysis
scripts/babel/setup_env.sh
```

The sbatch wrapper automatically uses `/home/andiongu/cua-failure-analysis/.venv`
when it exists.

## Smoke Test

Run from your local machine:

```bash
cd errorAnalysis
scripts/babel/submit_hf_analysis.sh \
  opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip
```

The script prints the run id and the remote output directory:

```text
/data/user_data/andiongu/cua_failure_analysis/outputs/<run_id>
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

- `/home/andiongu/cua-failure-analysis` for code, configs, and small logs only.
- the lab group space (`BABEL_GROUP_DIR`, 8TB) for the HF cache and selected zips
  when an allocation exists; otherwise `/data/user_data/andiongu/...` (500GB).
- `/data/user_data/andiongu/cua_failure_analysis/outputs` for reports.
- `/scratch` or the configured work root for temporary extraction.

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
