# autoResearch runbook

## Setup

```bash
cd autoResearch
pip install -e ../errorAnalysis     # provides cua_failure_analysis
pip install -e ".[dev]"
python -m pytest tests -q           # must be green before any loop session
```

## Offline detector loop (P0 — safe anywhere)

```bash
python scripts/run_loop.py --executor detector --proposals grid \
    --grid config/proposals_detector_grid.yaml --run-id det-YYYYMMDD
```

- Ledger: `data/ledger.jsonl` (append-only; re-runs dedupe by candidate hash).
- Best candidate: `data/best/candidate.yaml`.
- Summary: `data/loop_outputs/<run-id>/summary.md` — picked up by
  `ops/weekly_report.py`.

Score one candidate without the loop:

```bash
python scripts/score_candidate.py --candidate config/baseline_candidate.yaml
```

## Queue mode (P1 — authored experiments)

Append entries to `config/experiments_queue.yaml` (see file for shape), then:

```bash
python scripts/run_loop.py --executor detector --proposals queue --run-id q-YYYYMMDD
```

Judge-protocol entries in the queue need the judge executor (below).

## Live judge loop (P1 — needs endpoint; cost-capped)

Self-hosted vLLM judge (no marginal cost; meter still counts calls):

```bash
# on Babel/Bridges: serve the judge model first (see errorAnalysis/docs/vllm_runbook.md)
python scripts/run_loop.py --executor judge --proposals queue \
    --judge-url http://<node>:8000/v1 --run-id judge-YYYYMMDD
```

Paid API judge (e.g. the Sonnet 4.6 inter-annotator judge) — pricing comes
from `errorAnalysis/config/judge_pricing.yaml` and the $25 gate is enforced
up front:

```bash
python scripts/run_loop.py --executor judge --proposals queue \
    --judge-url <openai-compatible-url> --judge-api-key $KEY \
    --priced-model claude-sonnet-4-6 --cap-usd 25 --run-id judge-YYYYMMDD
```

Estimate before running (uses real trace sizes):

```bash
cd ../errorAnalysis
python scripts/estimate_judge_cost.py --traces-root data/traces --protocol v2
```

## LLM proposer (P2 — gated)

Requires Abdoul's approval + `ANTHROPIC_API_KEY`:

```bash
python scripts/run_loop.py --executor detector --proposals llm \
    --enable-llm-proposer --max-llm-proposals 10 --run-id llm-YYYYMMDD
```

## Swapping in the real gold eval set (when the ~10-trace study lands)

1. Build a new eval directory `data/eval_set_gold_v1/` with the same
   `eval_manifest.json` shape (`case_id`, `split`, `trace`, `gold_modes`
   multi-label, plus reference/context fields). Assign calibration/holdout
   before looking at any scores; keep the split fixed forever.
2. Compute `content_hash` with `auto_research.objective._hash_eval_content`.
3. Point the loop at it: `--eval-set data/eval_set_gold_v1`.
4. Keep the fixture set for CI; never mix the two in one ledger analysis
   (ledger rows carry `eval_set_hash`, so they are distinguishable).

## Reading the ledger

```bash
python - <<'EOF'
import json, pathlib
rows = [json.loads(x) for x in pathlib.Path("data/ledger.jsonl").read_text().splitlines()]
for r in rows:
    if r["verdict"] != "discarded":
        print(r["experiment_id"], r["verdict"], r["candidate_name"],
              r["primary_calibration"], r["primary_holdout"])
EOF
```

`kept_suspect_overfit` = kept on calibration but holdout dropped > epsilon —
treat as provisional and expand the eval set before trusting it.
