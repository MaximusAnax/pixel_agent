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
  exists (created once via `scripts/babel/setup_env.sh` on Babel after the first code
  sync). `submit_hf_analysis.sh` preserves `.venv` across syncs and refuses to submit
  without it.
- SSH to `login.babel.cs.cmu.edu` works non-interactively (key-based).

## Quick Reference

All commands run from the project directory (`babel.project_dir`).

| Step | Command |
|---|---|
| Pick a package | inspect `config/hf_osworld_packages.yaml` |
| Submit a job | `scripts/babel/submit_hf_analysis.sh <package.zip>` |
| Inspect queue | `ssh andiongu@login.babel.cs.cmu.edu squeue --me` |
| Sync outputs | `scripts/babel/sync_outputs.sh <run_id>` |
| Wait for job | `scripts/babel/wait_for_run.sh <slurm_job_id> <run_id>` |
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
   background and notify when done — use `wait_for_run.sh` (checks both `summary.md`
   and `sacct` so a failed job does not poll forever):

   ```bash
   scripts/babel/wait_for_run.sh <slurm_job_id> <run_id>
   ```

   Capture `<slurm_job_id>` from the `Submitted batch job NNNNN` line printed by
   `submit_hf_analysis.sh`. Run via `terminal(background=True, notify_on_complete=True)`,
   or register a `cronjob` that runs step 5 and reports back. Never tie up a synchronous
   `delegate_task` subagent waiting on Slurm. On a laptop, remind Andi to run
   `caffeinate -dims` so background SSH polls survive until the job finishes.
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
- If `submit_hf_analysis.sh` errors about a missing `.venv`, run
  `scripts/babel/setup_env.sh` on Babel once (after code is synced).
- Never poll with a bare `until [ -f summary.md ]` loop — use
  `scripts/babel/wait_for_run.sh` so Slurm failures exit instead of waiting forever.
- Best-effort labels are provisional. `Unresolved` / `needs_human_review=true` are
  adapter signals, not scientific conclusions.
- Do not re-run a run id that already has outputs unless Andi asks (no overwrites).

## Verification

A run is healthy when `data/babel_outputs/<run_id>/summary.md` exists locally and
reports episodes inventoried, episodes normalized, labels emitted, and adapter
gaps. If `episode_manifests.json` shows 0 normalized steps everywhere, the package
needs a specific adapter — surface `adapter_gaps.json` as the next action.

## Annotation-ready follow-ons (post–Phase 0)

After grounding freeze (`docs/GROUNDING_MANIFEST.md`), do **not** edit frozen
grounding docs. Operational work for annotation-ready infrastructure:

1. **Vendor OSWorld metadata** — pin SHAs in `config/osworld_sources.yaml`; run
   `scripts/vendor_osworld_metadata.py` for `pilot_task_ids`; generate per-func
   eval summaries (task-specific only).
2. **UI mockups first** — static HTML under `docs/mockups/`; Abdoul approval before
   Jinja/`packet.py` production UI.
3. **Human Agent (hybrid)** — `scripts/audit_human_actions.py` then
   `scripts/run_oracle_pilot.py` on Babel; cache grounding; ship screenshots to
   review packet **and** multimodal judge. `oracle_status`: pending|ready|partial|failed.
4. **Provisional rejudge** — `scripts/rejudge_pilot.py` with
   `judge_context_version: osworld_v1` **only after** Human Agent screenshots are
   ready. Run `estimate_judge_cost.py` (include human image tokens) + Abdoul
   approval. Never overwrite prior judge labels.
5. Rebuild review packet; discovery labeling by `abdoul`/`raghav` treats judge as
   provisional reference only.

Human reference is **non-binding** — full sequence for context; do not require
agent↔human step alignment.
