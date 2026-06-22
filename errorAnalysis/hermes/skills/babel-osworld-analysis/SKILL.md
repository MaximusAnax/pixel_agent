---
name: babel-osworld-analysis
description: Orchestrate remote failure analysis of OSWorld-Verified trajectory packages on the CMU Babel Slurm cluster, then sync compact artifacts back. Use for Phase 1 CUA failure analysis.
version: 1.0.0
author: pixelAgent / CUA Failure Analysis
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Research, HPC, Slurm, Babel, OSWorld, CUA]
    requires_toolsets: [terminal]
    config:
      - key: babel.project_dir
        description: Local path to the errorAnalysis project root (where scripts/babel/* live)
        default: "~/Documents/School/Research/pixelAgent/errorAnalysis"
        prompt: "Local errorAnalysis project directory"
---

# Babel OSWorld Failure Analysis

Submit, monitor, and collect remote OSWorld-Verified failure-analysis jobs on the
CMU Babel cluster without ever downloading raw trajectory zips locally.

## When to Use

Load this skill when Andi asks to analyze an OSWorld-Verified trajectory package
(e.g. an OpenCUA / Kimi / Claude Sonnet zip) on Babel, or to check/collect a
previously submitted run. Do NOT use it to run new OSWorld trajectories — Phase 1
only analyzes already-generated ones.

## Prerequisites

- `config/babel.env` exists (copy from `config/babel.env.example`). It is git-ignored.
- The repo has been synced to Babel and `/home/andiongu/cua-failure-analysis/.venv`
  exists (created once via `scripts/babel/setup_env.sh` on Babel).
- SSH to `login.babel.cs.cmu.edu` works non-interactively (key-based).

## Quick Reference

All commands run from the project directory (`babel.project_dir`).

| Step | Command |
|---|---|
| Pick a package | inspect `config/hf_osworld_packages.yaml` |
| Submit a job | `scripts/babel/submit_hf_analysis.sh <package.zip>` |
| Inspect queue | `ssh andiongu@login.babel.cs.cmu.edu squeue --me` |
| Sync outputs | `scripts/babel/sync_outputs.sh <run_id>` |
| Read result | `data/babel_outputs/<run_id>/summary.md` |

## Procedure

1. `cd` into the project directory (the `babel.project_dir` config value).
2. Confirm the target package with Andi if ambiguous; default smoke test is
   `opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip`.
3. Submit:

   ```bash
   scripts/babel/submit_hf_analysis.sh <package.zip>
   ```

   Capture the printed `RUN_ID` and the remote output dir
   (`/data/user_data/andiongu/cua_failure_analysis/outputs/<run_id>`).
4. The Slurm job is **asynchronous**. Do not block. Poll for completion in the
   background and notify when done — e.g.:

   ```bash
   ssh andiongu@login.babel.cs.cmu.edu \
     "until [ -f /data/user_data/andiongu/cua_failure_analysis/outputs/<run_id>/summary.md ]; do sleep 120; done; echo DONE"
   ```

   Run this via `terminal(background=True, notify_on_complete=True)`, or register a
   `cronjob` that runs step 5 and reports back. Never tie up a synchronous
   `delegate_task` subagent waiting on Slurm.
5. When `summary.md` exists remotely, sync only compact artifacts:

   ```bash
   scripts/babel/sync_outputs.sh <run_id>
   ```

   Artifacts land in `data/babel_outputs/<run_id>/` (json, jsonl, csv, md only).
6. Read `summary.md` first, then `adapter_gaps.json`, `failure_labels.jsonl`, and
   `human_review_queue.jsonl`. Report using the project Output Standard (see
   `AGENTS.md`).

## Analyzing Multiple Packages in Parallel

Use `delegate_task` with one child per package, each `toolsets=["terminal","file"]`.
Each child only *submits* (fast) and records its run id; do the long Slurm wait and
sync in the parent via background terminal / cron. Pass every child the absolute
project path and the exact submit command — subagents have no shared history.

## GPU Runs (only if Andi approves)

Phase 1 analysis is CPU-only. If a calibrated judge needs a GPU, set in
`config/babel.env`: `BABEL_PARTITION=general`, `BABEL_GPUS=1`,
`BABEL_GPU_TYPE=L40S`. The sbatch wrapper loads `cuda-12.9` automatically for GPU
jobs. An `oom_kill` means CPU RAM ran out — raise `BABEL_MEM`, not GPU count.

## Pitfalls

- Listing `/data/user_data` or `/data/group_data` from the login node may show
  empty dirs (AutoFS). The scripts `stat` full paths on the compute node to mount.
- `--gres` must include a GPU type (`gpu:L40S:1`), never `gpu:1`.
- Best-effort labels are provisional. `Unresolved` / `needs_human_review=true` are
  adapter signals, not scientific conclusions.
- Do not re-run a run id that already has outputs unless Andi asks (no overwrites).

## Verification

A run is healthy when `data/babel_outputs/<run_id>/summary.md` exists locally and
reports episodes inventoried, episodes normalized, labels emitted, and adapter
gaps. If `episode_manifests.json` shows 0 normalized steps everywhere, the package
needs a specific adapter — surface `adapter_gaps.json` as the next action.
