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
