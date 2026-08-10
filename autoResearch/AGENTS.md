# autoResearch — operating contract

Stage 2 of pixelAgent: a Karpathy-style autoresearch loop
([karpathy/autoresearch](https://github.com/karpathy/autoresearch)) that
optimizes the **attribution policy** (Tier-1 detector thresholds + VLM judge
protocol) against **agreement with gold failure labels**. Design rationale:
`docs/scoping_karpathy_autoresearch.md`. How to run: `docs/runbook.md`.

> One frozen eval set, one mutable candidate file, one scalar metric
> (multi-label macro-F1 vs gold), keep/discard on calibration, holdout
> recorded but never optimized.

## What this stage validates

RQ4 of `errorAnalysis/failureAnalysisFinalPlan.md`: *can a hybrid pipeline
(programmatic detectors + calibrated VLM judge) match human labels well
enough to scale?* — turned into a measurable, automatable optimization. The
2026-08-10 novelty scan (`docs/research/`) shows measurement validity is
exactly the unclaimed niche vs CUADebug (2608.02643) and 2606.14106.

## Hermes role

Hermes may: run the loop offline (`detector` executor, `grid`/`queue`
proposals), score candidates, append experiments to
`config/experiments_queue.yaml`, and report ledger results in weekly notes.

Hermes may not (without Abdoul's explicit go-ahead): run the `judge`
executor against paid APIs, enable `--proposals llm`, or submit cluster jobs.

## Non-negotiable boundaries

- **Never modify** `data/eval_set/` (hash-pinned; the runner hard-fails on
  drift), `src/auto_research/objective.py` metric definitions, the taxonomy,
  or gold labels — those change only by human-reviewed commit.
- **Never treat fixture-set scores as scientific results.** The current eval
  set is synthetic (see `data/eval_set/README.md`). Real gold labels from the
  inter-annotator study get their own eval set directory when they land.
- **Never spend past the cap**: judge runs use `CostMeter` (default $25/session,
  Decision 3). The loop stops; it does not ask forgiveness.
- **Ledger is append-only** (`data/ledger.jsonl`); never rewrite history.
- Anchors must not quote eval-set traces (leakage rule).

## Default flow (offline, safe to run anytime)

```bash
cd autoResearch
pip install -e ../errorAnalysis && pip install -e .
python -m pytest tests -q                      # 19 tests, no network
python scripts/build_eval_set.py               # only if eval set missing
python scripts/run_loop.py --executor detector --proposals grid \
    --run-id det-$(date +%Y%m%d)
cat data/loop_outputs/<run-id>/summary.md      # weekly_report.py picks this up
```

Judge mode (needs vLLM endpoint on Babel/Bridges, or API key + pricing):
see `docs/runbook.md` §Live judge.

## Layout

| Path | What |
| --- | --- |
| `config/baseline_candidate.yaml` | The mutable artifact's baseline (human-owned) |
| `config/proposals_detector_grid.yaml` | P0 grid proposals |
| `config/experiments_queue.yaml` | P1 authored experiment queue |
| `program.md` | Research directives for proposal agents |
| `data/eval_set/` | Frozen, hash-pinned eval fixtures |
| `data/ledger.jsonl` | Append-only experiment ledger |
| `data/best/candidate.yaml` | Current best candidate snapshot |
| `data/loop_outputs/<run>/summary.md` | Run summaries (weekly-report glob) |
| `src/auto_research/` | Loop library (objective, executors, loop, budget) |
| `hermes/skills/autoresearch-loop/` | Hermes skill for running sessions |

## Multi-agent notes

Subagents get absolute paths and this file's boundaries verbatim. A child
session running the loop returns: run_id, ledger delta (kept/discarded
counts), best candidate hash + scores, and the summary.md path. Long judge
runs poll with `wait`-style patterns — never block a delegate on a cluster
queue (see `docs/multi_idea_stages.md`).
