# 7 — Infrastructure

Hard-won operational knowledge. Most of this cost someone a day to learn.

---

## The rule

**All OSWorld VMs and inference run on Babel / PSC Bridges-2 — not locally, not on
AWS.** Decided 2026-06-24 and reaffirmed. The master plan's older "Option B: local
machine / Option C: AWS" language is superseded.

Corollaries from root `AGENTS.md`, non-negotiable:

- Never download OSWorld-Verified trajectory zips to the laptop.
- Never mirror the full Hugging Face dataset (~480 GB).
- Never use `/home/andiongu` on Babel for large zips, traces, or HF caches.
- **Shared lab work — code clone, outputs, review packets, annotations — lives
  under `/data/group_data/mattlab/pixel_agent/`.** See
  `errorAnalysis/docs/babel_hf_orchestration.md`.
- Never treat best-effort adapter labels **or provisional judge labels** as final
  scientific labels.
- Never launch large/expensive GPU jobs without Abdoul approving the reason.

### ⛔ Grounding freeze (2026-07-10)

`errorAnalysis/docs/GROUNDING_MANIFEST.md` freezes a specific file list. **No agent
or contributor edits them** during post–Phase 0 work; changes require a new
approved plan and Abdoul's explicit approval. Frozen:

`failureAnalysisFinalPlan.md` · `failureTaxonomy.md` · `failureStudyProtocol.md` ·
`failureAnalysisPlan.md` · `errorAnalysis/AGENTS.md` · `hermes/SOUL.md` ·
`hermes/skills/babel-osworld-analysis/SKILL.md` · **repo-root `AGENTS.md`** ·
`docs/GROUNDING_MANIFEST.md` itself.

**Not** frozen — edit freely: `trace_review_labeling.md`, `babel_hf_orchestration.md`,
`oracle_agent.md`, `docs/mockups/*`, templates, code, `config/*`. Also not frozen:
`ops/state/PROJECT_STATE.md` (regenerated) — but never hand-edit the managed
`PROJECT_STATE` block inside root `AGENTS.md`.

---

## PSC Bridges-2

| Item | Value |
|---|---|
| Login | `ssh <psc_username>@bridges2.psc.edu` |
| File transfer | `data.bridges2.psc.edu` — **not** the login nodes |
| Allocation / charge ID | `cis260099p` — pass `-A cis260099p` on **every** job |
| Partitions | `GPU-shared` (1–4 GPUs, cost-efficient) or `GPU` (full 8-GPU node) |
| Usernames | Abdoul `andiongue` · Raghav `rgupta19` |
| Known-good node | `v016` (GPU-shared) |
| Quotas | `projects`, `my_quotas` |
| Storage | Ocean — `$HOME`, `$PROJECT` |

**Never run vLLM, OSWorld, or training on login nodes.**

Interactive GPU session:

```bash
interact -A cis260099p -p GPU-shared --gres=gpu:1 -t 4:00:00
```

### ⚠️ The vLLM / CUDA trap — solved, read before touching the env

Bridges exposes **CUDA 12.6** via `module load cuda/12.6.1`. Two failure modes cost
Abdoul significant time:

1. In a Python 3.13 conda env, `pip install vllm` pulled **vLLM 0.23 built against
   CUDA 13** → `ImportError: libcudart.so.13: cannot open shared object file`.
2. Pinning `vllm==0.12.0` failed because pip fell back to the **source tarball**
   instead of a prebuilt wheel.

**Lab standard — use this:**

- **vLLM 0.11.0**
- **Python 3.11** conda env
- `module load cuda/12.6.1`

> Note this contradicts `failureStudyProtocol.md`, which still says
> `vllm>=0.12.0`. The protocol is wrong on this point. See
> [`08-decisions-and-questions.md`](08-decisions-and-questions.md).

Serving OpenCUA:

```bash
vllm serve xlangai/OpenCUA-7B \
  --trust-remote-code \
  --served-model-name opencua-7b \
  --host 0.0.0.0 --port 8000
```

Record the compute-node hostname (`hostname`) — OSWorld needs it to reach the API
at `http://<node>:8000/v1`.

Repo scripts: `errorAnalysis/scripts/bridges/` — `setup_vllm_env.sh`,
`vllm_serve_opencua.sh`, `vllm_serve_opencua.sbatch`, `interact_gpu.sh`,
`smoke_test_vllm.sh`, `diagnose_gpu_env.sh`. Runbook:
`errorAnalysis/docs/vllm_runbook.md`.

Bridges charges **Service Units** by node type and wall time — run a pilot first to
measure burn rate before scaling.

---

## CMU Babel

Primary cluster for the Hugging Face OSWorld-Verified trajectory analysis.

| Item | Value |
|---|---|
| Login | `ssh andiongu@login.babel.cs.cmu.edu` |
| Compute nodes | `babel-*`, reached via ProxyJump through the login host |
| Access | Andrew IDs; request via LTI intranet + safety quiz at [hpc.cs.cmu.edu](https://hpc.cs.cmu.edu/) |

### Storage — get this right

| Path | Size | Visible from | Use for |
|---|---|---|---|
| `/home/andiongu` | 100 GB | all nodes | **Code and small logs only** |
| `/data/user_data/andiongu` | 500 GB | compute nodes, persistent | HF cache, selected zips, normalized traces, outputs |
| `/data/group_data/<lab>` | 8 TB | compute nodes only (**not** login) | Large models/data — always in your own `$USER` subdir |
| `/data/datasets`, `/data/models` | — | — | Community data/models — **check here before downloading anything** |
| `/scratch` | — | node-local, auto-expunged | Temporary extraction only |

Image-heavy trajectory data grows fast in this field; Babel storage is expected to
be adequate, but check `/data/datasets` first every time.

### Slurm

```bash
# interactive
srun --partition debug ... --pty bash
# batch GPU
sbatch --partition general ...
```

- **GPU requests must name a type**: `--gres=gpu:L40S:1` — **never** `--gres=gpu:1`.
  `L40S` is the most plentiful; A100 and L40 are faster but scarcer.
- GPU jobs need `module load cuda-12.9` *(note: Babel 12.9, Bridges 12.6.1 — they
  differ)*.
- An `oom_kill` means **CPU RAM**, not GPU HBM — raise `--mem`.

### Phase 1 flow

Run everything from `errorAnalysis/`.

1. Confirm the package/model target — `config/hf_osworld_packages.yaml`.
2. Ensure the repo has been synced to Babel at least once.
3. Ensure `/home/andiongu/cua-failure-analysis/.venv` exists; if not, run
   `scripts/babel/setup_env.sh` on Babel after sync. `submit_hf_analysis.sh`
   preserves `.venv` across syncs and refuses to queue Slurm without it.
4. `scripts/babel/submit_hf_analysis.sh <zip>` — record the run id.
5. **Do not block on the Slurm job.** Poll with
   `scripts/babel/wait_for_run.sh <job_id> <run_id>` (checks `sacct`, not just
   `summary.md`) or a cron job. On a laptop, `caffeinate -dims` so polls survive
   sleep.
6. `scripts/babel/sync_outputs.sh <run_id>` → `data/babel_outputs/<run_id>` —
   compact outputs only.
7. Summarize `summary.md`, `adapter_gaps.json`, `failure_labels.jsonl`,
   `human_review_queue.jsonl`.

Detail: `errorAnalysis/docs/babel_hf_orchestration.md`,
`errorAnalysis/docs/babel_account_checklist.md`.

---

## Annotation workflow (laptop, not cluster)

Day-to-day discovery labeling runs **on your laptop**, not on Babel compute nodes.
Only `annotations.json` is shared, via sync scripts.

1. **Pull** the HTML packet once — screenshots + HTML only, no run videos.
2. **Each session:** pull shared annotations → `serve_review_packet.py` → label in
   the browser → saves auto-push to Babel with `--babel-sync`.
3. **After a batch:** pull annotations → run agreement / comparison reports.
4. **Later:** discuss disagreements → propose taxonomy revisions *(requires
   Abdoul's approval before editing the frozen `failureTaxonomy.md`)*.

Always pass `--annotator abdoul` or `--annotator raghav`; saves only touch your own
namespace. Active packet: `pilot_taxonomy_paired_20260703` (30 tasks × 2 models).
Judge labels are frozen in `packet_manifest.json`. Detail:
`errorAnalysis/docs/trace_review_labeling.md`.

## Human Agent (oracle) artifacts

Large PNGs live on Babel under the mattlab shared tree:

```text
config/osworld/<pin>/oracle/<domain>/<task_id>/
  human_traj.json
  human_step_1_obs.png
  ...
  grounding_cache.jsonl
```

`oracle_status` ∈ `ready` | `partial` | `failed` | `pending`. The multimodal
`osworld_v1` rejudge is gated on `ready` or `partial`. Detail:
`errorAnalysis/docs/oracle_agent.md`.

## Python package

```bash
cd errorAnalysis && pip install -e ".[dev]"
pytest
```

CLI entry points:

```bash
cua-attribute  --traces-root data/traces --output data/attributions.jsonl
cua-attribute  --traces-root data/traces --output data/attributions.jsonl \
               --judge-url http://v016:8000/v1 --judge-model opencua-7b
cua-agreement  --gold data/labeling/example_gold_labels.jsonl --output data/labeling/agreement.json
cua-prevalence --attributions data/attributions.jsonl --output data/prevalence.json
```

Package layout — `src/cua_failure_analysis/`: `detectors/tier1.py`,
`attribution/{pipeline,first_failure}.py`, `judge/{client,prompts}.py`,
`labeling/{agreement,gold_set}.py`, `stats/prevalence.py`, `trace/schema.py`,
`taxonomy.py`.

Config is git-ignored — copy the examples:
`config/babel.env.example` → `config/babel.env`,
`config/bridges.env.example` → `config/bridges.env`.

---

## Trace schema

```json
{
  "task_id": "string", "seed": 0, "step": 0,
  "screenshot_path": "string",
  "action": {}, "coords": [0, 0], "cot": "string",
  "eval_signals": {}, "a11y_snippet": {},
  "task_tags": ["relational", "underspecified", "infeasible",
                "fine_manipulation", "cross_app", "zoom_stress"]
}
```

Judge output:

```json
{ "primary_mode": "leaf_name", "secondary_modes": [], "propagated": false,
  "tier_used": "programmatic|a11y|judge", "evidence_cot_span": "string",
  "confidence": 0.0, "t_star": 0 }
```

Task tags must be **pre-registered at task selection** — controlled-track leaves
may not be assigned without the matching tag.

---

## Ops automation

From the repo root:

```bash
python ops/weekly_report.py --days 7
python ops/pull_gdoc_notes.py --date YYYY-MM-DD --section-only
python ops/synthesize_state.py
```

- Google Docs ingest uses a **service account** —
  `pixelagent@pixelagent-500520.iam.gserviceaccount.com`, key at
  `ops/config/gdoc-service-account.json` (git-ignored). The doc must be shared with
  that address as Viewer.
- Config: `ops/config/meetings.env` — `MEETING_GDOC_ID`, meeting window,
  `ANTHROPIC_API_KEY`.
- CI: `.github/workflows/weekly-report.yml`, `post-meeting-sync.yml`.
- **The `PROJECT_STATE` block in root `AGENTS.md` is generated. Never hand-edit it.**

> Gotcha, confirmed 2026-08-10: the **Drive API is disabled** in GCP project
> `pixelagent-500520` (project number 804624298804), so the service account can read
> Docs by ID but cannot list folders. The Docs API works fine. Enable Drive API if
> you want folder enumeration from the scripts. A separate interactive Google Drive
> connector is available in agent sessions and does not have this limitation.

---

## Misc

Keep a Mac awake through a long run:

```bash
sudo pmset disablesleep 1   # disable
sudo pmset disablesleep 0   # re-enable
```

Or `caffeinate -dims <command>` for a single command — preferred, since it
auto-reverts.
