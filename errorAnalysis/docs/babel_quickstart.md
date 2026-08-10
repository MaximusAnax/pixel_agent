# Babel quick-start (GPU queues, env setup, remote workflow)

> PROJECT_STATE action item: "Write up Babel quick-start guide (GPU queues,
> env setup on remote machine)." Companion docs:
> `babel_account_checklist.md` (getting access),
> `babel_hf_orchestration.md` (the full HF-trajectory analysis workflow).

## 0. Access

Andrew ID + LTI Babel account (see `babel_account_checklist.md`). Then:

```bash
ssh <andrewid>@babel.lti.cs.cmu.edu
```

Put host/user/paths in `config/babel.env` (copy from `config/babel.env.example`).

## 1. Storage map — where things go (and never go)

| Path | Use | Notes |
|---|---|---|
| `/home/<user>` | code, small configs | **never** large zips, traces, HF caches |
| `/data/user_data/<user>` | run outputs, bounded extracts, HF cache | primary working storage |
| `/data/datasets` | shared read-only datasets | check before downloading anything |
| `/scratch` | job-local scratch | wiped; bounded extracts during jobs |

Repo boundaries (root AGENTS.md): never mirror the full HF OSWorld dataset
(~480GB); never stage large artifacts in `$HOME`; sync only compact
JSONL/CSV/MD summaries back to the laptop.

## 2. GPU queues (Slurm)

```bash
sinfo -o "%P %G %D %t"            # partitions + GPU types + availability
squeue -u $USER                   # your queue
```

- L40S GPUs are the project default for OSWorld VM + inference jobs
  (Decision 1). Request e.g. `--gres=gpu:L40S:1`.
- Interactive debugging: `srun --partition=general --gres=gpu:1 --mem=32G \
  --time=2:00:00 --pty bash` (adjust partition names to what `sinfo` shows).
- Batch: `sbatch scripts/babel/analyze_hf_osworld.sbatch` via the local
  helper `scripts/babel/submit_hf_analysis.sh` (syncs code first).
- Poll without blocking an agent: `scripts/babel/wait_for_run.sh <jobid>`.

## 3. Environment setup (one-time, on Babel)

```bash
bash scripts/babel/setup_env.sh    # python env under /data/user_data, persists across syncs
```

The env lives outside the rsynced tree so re-syncing code never rebuilds it.
Set `HF_HOME=/data/user_data/<user>/hf_cache` before anything touches
Hugging Face.

## 4. Standard workflow (from the laptop)

```bash
# 1. sync code + submit analysis job
bash scripts/babel/submit_hf_analysis.sh

# 2. wait / poll
bash scripts/babel/wait_for_run.sh <jobid>

# 3. stage compact outputs to login-visible storage, then pull them
bash scripts/babel/stage_outputs_to_home.sh <run_id>
bash scripts/babel/sync_outputs.sh <run_id>
```

Outputs land under `errorAnalysis/data/babel_outputs/<run_id>/` locally —
`ops/weekly_report.py` picks up each run's `summary.md` automatically.

## 5. Serving a judge/agent model on Babel

Same pattern as Bridges (see `bridges_standard_env.md` for the vLLM 0.11.0 /
CUDA 12 standard — verify Babel's CUDA modules with `module avail cuda`):

```bash
srun --gres=gpu:L40S:1 --mem=48G --time=4:00:00 --pty bash
module load cuda/12.6.1   # or Babel's closest CUDA 12.x
conda activate cua-vllm
vllm serve <model> --port 8000 --trust-remote-code
```

Then point clients (attribution pipeline, autoResearch judge executor) at
`http://<node>:8000/v1`.

## 6. Etiquette / guardrails

- GPU jobs need a stated reason Abdoul has approved (root AGENTS.md).
- Time-limit every job; prefer `GPU-shared`-style smallest allocations.
- Keep run artifacts compact and inspectable (summary.md convention).
