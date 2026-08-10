# autoresearch-loop

Run a pixelAgent autoresearch session: calibrate the failure-attribution
pipeline against gold labels via the keep/discard loop.

## When to use

- Weekly, or whenever new experiments land in `config/experiments_queue.yaml`.
- After the eval set changes by human commit (rebaseline the ledger with a
  fresh run-id).
- Never for paid judge runs or the LLM proposer without Abdoul's explicit
  approval in the current conversation.

## Steps

1. `cd <repo>/autoResearch` (absolute path from the parent session).
2. Preflight: `python -m pytest tests -q` — abort and report if red.
3. Run: `python scripts/run_loop.py --executor detector --proposals grid --run-id det-$(date +%Y%m%d)`
   (or `--proposals queue` when the queue has unrun entries; the ledger
   dedupes, so running both is safe).
4. Read `data/loop_outputs/<run-id>/summary.md` and the tail of
   `data/ledger.jsonl`.
5. Report back: run_id, experiments run, kept candidates with calibration AND
   holdout deltas, best candidate hash, summary path. Flag any
   `kept_suspect_overfit` verdicts explicitly.
6. If a kept candidate beats the committed baseline meaningfully, propose (do
   not perform) an update to `config/baseline_candidate.yaml` for Abdoul's
   review, quoting both split scores.

## Boundaries (from autoResearch/AGENTS.md — binding)

Never modify eval set, metric code, taxonomy, or gold labels; never exceed
the $25 judge cap; ledger is append-only; fixture scores are not science.
