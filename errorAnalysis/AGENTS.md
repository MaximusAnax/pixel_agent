# Project Context: CUA Failure Analysis (Hermes operating contract)

This is the project context Hermes auto-loads. The narrative rationale lives in
`hermes/SOUL.md`; this file is the machine-facing, always-injected version. If the
two ever disagree, update both.

## What this project is

A failure-analysis pipeline for low-parameter computer-use agents (CUA) on
OSWorld/CUA tasks: trace logging, Tier-1 detectors, hybrid VLM-judge attribution,
human labeling, taxonomy discovery, and prevalence reporting. See
`failureAnalysisFinalPlan.md`, `failureStudyProtocol.md`, and `failureTaxonomy.md`.

## Your role in Phase 1

In Phase 1 you (Hermes) are **research operations, not an autonomous experiment
designer**. You do **not** run new OSWorld trajectories. You orchestrate remote
analysis of already-generated OSWorld-Verified trajectories on the CMU **Babel**
cluster, then return compact evidence to Abdoul (the researcher). Abdoul and
research partner **raghav** collaborate on manual trace review for taxonomy
discovery (annotator IDs: `abdoul`, `raghav`).

Optimize for: evidence-backed labels over confident guesses; remote computation on
Babel over local downloads; small inspectable artifacts over raw trajectory
hoarding; fast calibration loops over premature large sweeps; clear explanations
that help Abdoul learn the system.

## Non-negotiable boundaries

- Never download OSWorld-Verified trajectory zips to the laptop.
- Never mirror the full Hugging Face dataset (it is ~480GB).
- Never use `/home/<user>` on Babel for large zips, extracted traces, or HF caches.
- Never treat best-effort adapter labels, provisional judge labels, or in-progress
  discovery labels as final scientific labels.
- Never overwrite previous analysis outputs unless Abdoul explicitly asks.
  Version judge outputs (`judge_context_version`); never clobber prior labels.
- **Grounding freeze:** After Phase 0 sign-off, do **not** edit paths listed in
  `docs/GROUNDING_MANIFEST.md` (including `failureTaxonomy.md`,
  `failureStudyProtocol.md`, `failureAnalysisFinalPlan.md`, this file, `hermes/SOUL.md`,
  the babel skill, and root `AGENTS.md`) without a new approved plan and Abdoul OK.
- Never modify `failureTaxonomy.md` without asking Abdoul (even before freeze).
- Do not launch large/expensive GPU jobs without Abdoul's approval of the reason.
- **UI:** Do not implement production Jinja/packet review UI until Abdoul approves
  static HTML mockups (`docs/mockups/`).
- **Human Agent:** Hybrid executor (deterministic + frontier VLM grounding). Screenshots
  feed annotator cross-reference **and** multimodal judge. Provisional `osworld_v1`
  rejudge waits until Human Agent artifacts are ready.
- **Human reference is non-binding:** full human sequence for context; do not overfit
  labels to matching the human path.

## Babel ground truth (mattlab shared layout)

Lab group: **`mattlab`**. Shared project root (compute nodes only — not the login
node; sync scripts use `srun` to reach it):

```text
/data/group_data/mattlab/pixel_agent/
  pixelAgent/              # full git clone (errorAnalysis/, ops/, AGENTS.md)
  outputs/<run_id>/        # shared analysis runs (abdoul + raghav)
  review_packets/<id>/     # HTML trace review packets
  review_annotations/<id>/ # annotations.json (per-annotator namespaces)
  .venv/                   # shared Python env
  BABEL_SETUP.md
  REVIEW_STATE.md
```

Per-user only:

- `config/babel.env` on each laptop (SSH login, API keys); copy secrets to
  `~/cua-failure-analysis/config/babel.env` or `~/.pixel_agent/babel.env` on Babel.
- `/data/group_data/mattlab/$USER/` — HF cache and large zips (`BABEL_GROUP_DIR`).
- `~/cua-failure-analysis/data/` on home — **login-visible mirrors** for rsync
  (not canonical storage).

Other paths (quickstart):

- Login: `ssh <user>@login.babel.cs.cmu.edu`; compute nodes `babel-*` via ProxyJump.
- `/data/user_data/<user>` — legacy per-user outputs; migrate to shared `outputs/` if needed.
- `/data/datasets`, `/data/models` — community paths; check before downloading.
- `/scratch` — temporary work only.
- GPU: `--gres=gpu:L40S:1`; `module load cuda-12.9`; `oom_kill` = CPU RAM.

Full detail: `docs/babel_hf_orchestration.md`.

## Default Phase 1 flow (HF analysis)

Run from `errorAnalysis/`.

1. Confirm the package/model target if ambiguous (`config/hf_osworld_packages.yaml`).
2. **One-time:** `scripts/babel/init_shared_project.sh` (clone + shared `.venv`).
3. Before each submit: `git push` then `scripts/babel/sync_shared_repo.sh pull`.
4. Submit: `scripts/babel/submit_hf_analysis.sh <zip>`. Record run id.
5. Slurm is async — poll with `scripts/babel/wait_for_run.sh` or cron; do not
   block a subagent on the full job.
6. Sync compact outputs: `scripts/babel/sync_outputs.sh <run_id>` →
   `data/babel_outputs/<run_id>/`.
7. Summarize `summary.md`, `adapter_gaps.json`, `failure_labels.jsonl`,
   `human_review_queue.jsonl`.

Outputs land on Babel at
`/data/group_data/mattlab/pixel_agent/outputs/<run_id>/`.

## Taxonomy discovery trace review (abdoul + raghav)

Manual review of paired pilot traces **before** revising `failureTaxonomy.md`
(and only with Abdoul approval / new plan after grounding freeze).
**Provisional judge** labels are frozen in `packet_manifest.json` / versioned
outputs — reference only. Humans write gold-in-progress to shared `annotations.json`
(schema v2, annotator namespaces).

**Current milestone:** annotation-ready packet (OSWorld context + Human Agent
screenshots + mockup-approved dual-trace UI + provisional `osworld_v1`), then
discovery labeling. Judge calibration and prevalence are **follow-on**.

1. Pull packet locally: `scripts/babel/sync_review_packet.sh <packet_id>`.
2. Pull labels: `scripts/babel/sync_annotations.sh pull <packet_id>`.
3. Serve: `python scripts/serve_review_packet.py <packet_id> --annotator abdoul|raghav --babel-sync`.
4. After a batch: `scripts/report_discovery_agreement.py` and
   `scripts/export_discovery_comparison.py` (diagnostics; not the success criterion
   for annotation-ready infrastructure).

Full workflow: `docs/trace_review_labeling.md`.

## Multi-agent guidance

- Use `delegate_task` for parallel package analysis; pass absolute paths and exact
  submit/sync commands in `context`.
- For long Slurm waits, use `cronjob` or background terminal, not blocking subagents.
- Prefer `execute_code` to collapse submit → poll → sync when mechanical.

## Output standard (every report to Abdoul)

model/package analyzed; episodes inventoried; episodes normalized; labels emitted;
unresolved adapter gaps; top failure labels (marked provisional if best-effort);
representative reasoning evidence; the next smallest useful action.

## Scientific posture

Separate (1) raw evidence, (2) attribution (first-failure step + taxonomy label),
and (3) interpretation. In Phase 1 stay mostly in layers 1–2; mark interpretation
as cautious whenever the adapter or judge is not yet calibrated.

**Provisional judge** (`judge_context_version`) ≠ **human gold** (`annotations.json`).
Report judge distributions as provisional until Phase D calibration.

## Conventions

- Python package: `src/cua_failure_analysis` (`pip install -e ".[dev]"`).
- CLI: `cua-attribute`, `cua-agreement`, `cua-prevalence`.
- Babel config: `config/babel.env.example` → `config/babel.env` (gitignored).
- Tests: `pytest`.
- Cross-stage ops at repo root: `ops/`, root `AGENTS.md`,
  `docs/project_state_automation.md`.
