# Bridges-2 lab-standard environment (share with the team)

> PROJECT_STATE action item: "Document and share lab-standard Bridges setup:
> conda env name, `module load cuda/12.6.1`, vLLM 0.11.0." Decision source:
> meeting 2026-08-07 (Decision 2). This supersedes the older `>=0.12.0` note
> in `failureAnalysisFinalPlan.md` — 0.12/0.23 wheels pull CUDA 13 and break
> against Bridges' CUDA 12 modules (`libcudart.so.13` ImportError).

## The standard, in one block

```bash
ssh <user>@bridges2.psc.edu
module load cuda/12.6.1                  # every session, before anything CUDA
conda activate cua-vllm                  # Python 3.11 env, name: cua-vllm
python -c "import vllm; print(vllm.__version__)"   # must print 0.11.0
```

| Item | Standard | Why |
|---|---|---|
| Conda env name | `cua-vllm` | created by `scripts/bridges/setup_vllm_env.sh` |
| Python | 3.11 | matches vLLM 0.11.0 wheels |
| CUDA module | `cuda/12.6.1` | Bridges provides CUDA 12; pip CUDA-13 wheels fail |
| vLLM | **0.11.0** (pinned) | 0.12.0 / 0.23.x had CUDA incompatibility on Bridges |
| Allocation | `cis260099p` | pass `-A cis260099p` on every job |
| Partition | `GPU-shared` (1–4 GPUs) | cost-efficient; `GPU` only for full-node needs |

## First-time setup

```bash
bash scripts/bridges/setup_vllm_env.sh      # creates cua-vllm with vllm==0.11.0
```

(Override the pin only deliberately: `VLLM_PIN=x.y.z bash scripts/bridges/setup_vllm_env.sh`.)

## Serving + smoke test

```bash
interact -A cis260099p -p GPU-shared --gres=gpu:1     # get a compute node
module load cuda/12.6.1 && conda activate cua-vllm
bash scripts/bridges/vllm_serve_opencua.sh            # or sbatch scripts/bridges/vllm_serve_opencua.sbatch
bash scripts/bridges/smoke_test_vllm.sh <node>.ib.bridges2.psc.edu 8000
```

Never run vLLM or heavy jobs on login nodes. Full troubleshooting:
`docs/vllm_runbook.md`.

## Accounts

- Abdoul: `andiongue` · Raghav: `rgupta19`
- Check quota/allocation: `projects`, `my_quotas`
- File transfer host: `data.bridges2.psc.edu`
