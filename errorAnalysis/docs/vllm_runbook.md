# vLLM + OSWorld runbook

## OpenCUA-7B (Bridges)

### One-time setup (on GPU node `v016`)

Your `py313` env installed **vllm 0.23.0** with **CUDA 13** wheels. Bridges provides **CUDA 12** via modules, which causes:

```
ImportError: libcudart.so.13: cannot open shared object file
```

**Fix:** load Bridges CUDA + use a pinned vllm in a Python 3.11 env:

```bash
# Inside GPU allocation (interact -A cis260099p -p GPU-shared --gres=gpu:1)
module load anaconda3
bash scripts/bridges/setup_vllm_env.sh    # creates cua-vllm, installs vllm==0.12.0
conda activate cua-vllm
bash scripts/bridges/diagnose_gpu_env.sh  # optional sanity check
bash scripts/bridges/vllm_serve_opencua.sh
```

Every new session on Bridges:

```bash
module load anaconda3
module load cuda/12.6.1
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
conda activate cua-vllm
```

### Serve

```bash
# Interactive
interact -A cis260099p -p GPU-shared --gres=gpu:1 -t 4:00:00
bash scripts/bridges/vllm_serve_opencua.sh

# Smoke test (same node or second SSH to v016)
bash scripts/bridges/smoke_test_vllm.sh v016.ib.bridges2.psc.edu 8000

# Batch (24h)
mkdir -p logs
sbatch scripts/bridges/vllm_serve_opencua.sbatch
```

### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `libcudart.so.13` missing | pip vllm 0.23 + CUDA 13 vs Bridges CUDA 12 | `setup_vllm_env.sh` + `module load cuda/12.6.1` |
| vllm import fails | Wrong env / no GPU node | Run on compute node inside `interact`, not login |
| OOM on 7B | GPU too small | Add `--gpu-memory-utilization 0.9` or use A100 partition |

Endpoint after serve: `http://v016.ib.bridges2.psc.edu:8000/v1` (use `hostname` on your node).

OSWorld (separate VM host):

```bash
export OPENAI_BASE_URL=http://<vllm-node>:8000/v1
export MODEL_NAME=opencua-7b

cd /path/to/OSWorld
python run_multienv_opencua.py \
  --headless \
  --observation_type screenshot \
  --model opencua-7b \
  --result_dir ./results \
  --test_all_meta_path evaluation_examples/test_all_no_gdrive.json \
  --max_steps 100 \
  --num_envs 1 \
  --coordinate_type qwen25
```

## Qwen3.5-VL-0.8B (separate adapter)

- Serve with vLLM: `Qwen/Qwen3.5-VL-0.8B-Instruct` + `--trust-remote-code`
- Use OSWorld `qwen3vl` agent path ([OSWorld #441](https://github.com/xlang-ai/OSWorld/issues/441))
- **Do not** reuse OpenCUA chat template or `coordinate_type qwen25`

## Trace logging hook

In your OSWorld agent wrapper, import `TraceLogger` and `TraceStep` from `cua_failure_analysis.trace.schema` and call `log_step` after each action. See `data/pilot/sample_trace.jsonl`.

## Core study driver

```bash
python scripts/run_core_study.py --phase pilot   # 30 tasks
python scripts/run_core_study.py --phase core  # 100 tasks
```
