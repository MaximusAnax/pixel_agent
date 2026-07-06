# Whole-trajectory failure judge (local vLLM and/or Claude API)

Classifies *why* a computer-use agent (CUA) failed an OSWorld-Verified task by
feeding a VLM "judge" the **entire** failed trajectory (full step log + a sampled
set of screenshots) and having it emit one taxonomy label plus an analysis,
category, first-failing step, secondaries, and confidence.

This is the **whole-trajectory** counterpart to the per-step `attribution`
pipeline in the parent package. Two interchangeable backends emit the **same**
`Classification` schema, so their labels are directly comparable:

| backend | how | where | reliability |
|---|---|---|---|
| `local` | vLLM offline batched, guided-JSON decoding (Qwen2.5-VL 7B/32B/A3B) | GPU (Babel) | ~100 % parse |
| `api`   | Claude with a forced tool schema (same prompt/images) | anywhere + `ANTHROPIC_API_KEY` | structured output |

Merged from `osworld_traj_analysis/`. It keeps its own snake_case enum taxonomy
(`taxonomy.py`, 14 modes + `other`) — the schema, viewer, and existing
`classifications_*.jsonl` are keyed to it. (The parent package's 16-leaf
`FailureLeaf` taxonomy adds *Hidden Operation Blindness* and *Cross-Application
Context Loss*; reconciling the two is a deliberate, deferred research decision.)

## Layout
- `taxonomy.py` — 14 failure modes + 2 categories (+`other`) with definitions.
- `schema.py` — Pydantic output schema (`Classification`) used for both guided
  decoding (local) and the Anthropic tool `input_schema` (api).
- `judge_prompt.py` — system prompt + builds the judge messages (full text log +
  sampled screenshot placeholders).
- `parse_trajs.py` — unzipped OSWorld run → normalized `failures.jsonl`.
- `judge_common.py` — shared image selection, parsing/validation, record shape.
- `backends/local_vllm.py`, `backends/anthropic_api.py` — the two backends.
- `run_judge.py` — unified runner (`--backend local|api|both`).
- `aggregate.py` / `compare_judges.py` — tables/figures/report; judge-vs-judge agreement.
- `build_viewer.py` + `viewer_assets/` — static human-labeling + judge-comparison viewer.
- `jobs/*.sbatch` — SLURM wrappers for the local backend.

## Pipeline (run from `errorAnalysis/`)
```bash
pip install -e ".[dev]"          # local backend also needs: pip install -e ".[local-judge]" (GPU)

# 1. Normalize failed trajectories (per run-root; appends).
cua-traj-parse --run-root ../path/to/unzipped_run --model opencua-7b \
    --osworld ../path/to/OSWorld/evaluation_examples/examples \
    --out outputs/failures.jsonl

# 2a. Local judge (GPU) — via SLURM:
sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge.sbatch --limit 40   # validate
sbatch src/cua_failure_analysis/trajectory_judge/jobs/judge.sbatch               # full (resumes)

# 2b. Claude API judge (no GPU):
export ANTHROPIC_API_KEY=...
cua-traj-judge --failures outputs/failures.jsonl --backend api \
    --api-model claude-sonnet-4-6 --api-out outputs/classifications_api.jsonl

# 2c. Both on the SAME sample (two output files), for an apples-to-apples compare:
cua-traj-judge --failures outputs/failures.jsonl --backend both --limit 40

# 3. Compare the two judges and aggregate.
cua-traj-compare --a outputs/classifications_local.jsonl \
    --b outputs/classifications_api.jsonl --outdir outputs
cua-traj-aggregate --classifications outputs/classifications_local.jsonl --outdir outputs

# 4. Build the human-review viewer (the two judge columns take any two files).
cua-traj-viewer --failures outputs/failures.jsonl \
    --judge-7b outputs/classifications_local.jsonl \
    --judge-32b outputs/classifications_api.jsonl \
    --outdir viewer
bash viewer/serve.sh   # then port-forward, or open viewer/index.html via file://
```

## Output schema (`classifications*.jsonl`)
One JSON object per (trajectory, backend):
`uid, model, domain, task_id, reward, num_steps, n_images, judge_backend,
judge_model, parse_ok, classification{...}, raw` (+ `usage` for the API backend).
`classification.category` is the authoritative category *derived* from the primary
mode; the model's own category is preserved as `category_model` with a
`category_mismatch` flag.

## Notes
- The judge feeds the full step log but only ~10 sampled, downscaled screenshots
  per trajectory (first + keyframes + last few) to stay within context.
- `--backend both` selects one deterministic `--limit` sample and judges the same
  trajectories with local and API, so the outputs line up 1:1.
- Runs are resumable — UIDs already in an output file are skipped.
- `outputs/` and the built `viewer/` are git-ignored (large / generated); the
  viewer *template* under `viewer_assets/` is tracked.
- This subpackage uses 4-space indentation (as merged from osworld); the rest of
  `cua_failure_analysis` uses 2-space.
