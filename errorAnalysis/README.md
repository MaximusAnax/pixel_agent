# CUA Failure Analysis

Implementation of the [failureAnalysisFinalPlan.md](failureAnalysisFinalPlan.md) pipeline: trace logging, Tier-1 detectors, hybrid VLM-judge attribution, human labeling, and prevalence reporting.

## Quick start

```bash
pip install -e ".[dev]"
python scripts/build_stratified_tasks.py      # config/stratified_tasks.json (100 tasks)
python scripts/run_core_study.py --phase pilot
pytest
```

## Bridges (PSC)

```bash
cp config/bridges.env.example config/bridges.env   # edit if needed
interact -A cis260099p -p GPU-shared --gres=gpu:1 -t 4:00:00
bash scripts/bridges/vllm_serve_opencua.sh
```

See [docs/vllm_runbook.md](docs/vllm_runbook.md) and [failureStudyProtocol.md](failureStudyProtocol.md).

## Pipeline

```bash
# Attribute failed traces (programmatic only)
cua-attribute --traces-root data/traces --output data/attributions.jsonl

# With VLM judge fallback
cua-attribute --traces-root data/traces --output data/attributions.jsonl \
  --judge-url http://v016:8000/v1 --judge-model opencua-7b

# Agreement + prevalence
cua-agreement --gold data/labeling/example_gold_labels.jsonl --output data/labeling/agreement.json
cua-prevalence --attributions data/attributions.jsonl --output data/prevalence.json
```

## Babel + Hugging Face OSWorld-Verified

Phase 1 uses Babel as the remote backend for large HF trajectory packages. Do
not download OSWorld-Verified zips to the laptop.

```bash
cp config/babel.env.example config/babel.env

# One-time shared Babel project (mattlab):
source config/babel.env
scripts/babel/init_shared_project.sh

# Before each job:
git push && scripts/babel/sync_shared_repo.sh pull

scripts/babel/submit_hf_analysis.sh \
  opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip

# After the Slurm job completes:
scripts/babel/sync_outputs.sh <run_id>
```

See [docs/babel_hf_orchestration.md](docs/babel_hf_orchestration.md),
[docs/trace_review_labeling.md](docs/trace_review_labeling.md) (multi-annotator trace review),
and [hermes/SOUL.md](hermes/SOUL.md).

To drive this through the Hermes agent (multi-agent orchestration), follow
[docs/hermes_setup.md](docs/hermes_setup.md). Project context lives in
[AGENTS.md](AGENTS.md); the runnable workflow is the
`hermes/skills/babel-osworld-analysis` skill.

## Project-state automation (repo root)

Cross-stage weekly reports, Google Doc meeting notes, and Hermes live context live
at the **pixelAgent repo root**, not in this stage directory:

- [`../ops/`](../ops/README.md) — scripts and artifacts
- [`../docs/meeting_notes_workflow.md`](../docs/meeting_notes_workflow.md)
- [`../docs/project_state_automation.md`](../docs/project_state_automation.md)
- [`../hermes/skills/project-state-sync/`](../hermes/skills/project-state-sync/SKILL.md)

Run from the repo root: `python ops/weekly_report.py`, `python ops/pull_gdoc_notes.py`, etc.
The managed **Live project state** block is in root [`../AGENTS.md`](../AGENTS.md).

## Layout

```
config/           stratified tasks, models, judge anchors, bridges env
docs/             VM strategy, Babel checklist, vLLM runbook
scripts/          Bridges SLURM, core study matrix, AgentNetBench pilot
src/cua_failure_analysis/   Python package
data/             pilot traces, labeling templates, run matrices
tests/
```

## Documents

- [failureTaxonomy.md](failureTaxonomy.md) — 16 leaves + decision rules
- [failureStudyProtocol.md](failureStudyProtocol.md) — methodology
- [failureAnalysisPlan.md](failureAnalysisPlan.md) — experiments
