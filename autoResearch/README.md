# autoResearch

Karpathy-style autoresearch loop for pixelAgent: an agent-runnable
**propose → evaluate → keep/discard** loop that calibrates the failure-attribution
pipeline (Tier-1 detectors + VLM judge) against gold labels.

- **Why / design:** [docs/scoping_karpathy_autoresearch.md](docs/scoping_karpathy_autoresearch.md)
- **Operating contract & boundaries:** [AGENTS.md](AGENTS.md)
- **How to run:** [docs/runbook.md](docs/runbook.md)
- **Directives for proposal agents:** [program.md](program.md)

## 60-second demo (offline, no keys, ~seconds)

```bash
pip install -e ../errorAnalysis && pip install -e ".[dev]"
python -m pytest tests -q
python scripts/run_loop.py --executor detector --proposals grid --run-id demo
```

Expected shape of the result (exact numbers depend on the pinned eval set):
the baseline detector config scores ~0.72 calibration macro-F1; the loop
sweeps 54 threshold combinations, keeps ~2 successive improvements
(~0.83 calibration), and the holdout score rises with it (0.17 → 0.60) —
improvements that generalize, found autonomously, at $0.

## The mapping (one line)

karpathy/autoresearch: frozen `prepare.py` + mutable `train.py` + `program.md`
+ 5-minute budget + `val_bpb` ⇒ here: frozen eval set + mutable
`candidate.yaml` + `program.md` + cost-capped eval pass + multi-label macro-F1
vs gold.
