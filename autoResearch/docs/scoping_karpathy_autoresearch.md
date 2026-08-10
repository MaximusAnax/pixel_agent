# Scoping: Karpathy-style autoresearch for pixelAgent

**Date:** 2026-08-10
**Author:** Claude (research-ops), for Abdoul's review
**Status:** Proposal + working implementation (P0 shipped in this branch)

---

## 1. What Karpathy's autoresearch is

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) (released 2026-03-07) gives an
AI agent a small but *real* LLM training setup and lets it experiment autonomously:
modify code, train ~5 minutes, check whether the metric improved, keep or discard,
repeat overnight. In its first demonstration it ran ~700 experiments over two days
and found ~20 independent training improvements without human intervention
([Fortune coverage](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/),
[technical walkthrough](https://kingy.ai/ai/autoresearch-karpathys-minimal-agent-loop-for-autonomous-llm-experimentation/)).

The design is deliberately minimal — **"one GPU, one file, one metric"**:

| Piece | Role |
|---|---|
| `prepare.py` | **Frozen.** Data download, tokenizer, dataloader, eval utilities. Agents never touch it. |
| `train.py` | **The one mutable file.** Model, optimizer, training loop. Everything in it is fair game. |
| `program.md` | **Natural-language research directives.** A "super lightweight skill" humans edit to steer the agent. |
| Budget | Every experiment trains **exactly 5 minutes** wall-clock → experiments are directly comparable, ~100/night. |
| Metric | **`val_bpb`** (validation bits per byte) — a single scalar, vocab-size-independent so architectural changes compare fairly. |
| Loop | Read directives → edit `train.py` → run → observe metric → keep/discard → repeat. Scope contained to one file keeps "diffs reviewable". |

Karpathy's explicit advice for forks: shrink the knobs to your compute, keep the
three-file decomposition, and hand the agent the full source plus an adaptation guide.

## 2. Why this maps onto pixelAgent

pixelAgent's Phase 1 (`errorAnalysis/`) has a component with *exactly* the right shape:
**judge/attribution calibration** (Phase D of `failureStudyProtocol.md`, RQ4 of
`failureAnalysisFinalPlan.md`: "Can a hybrid pipeline match human labels well enough to scale?").

Calibration is an optimization problem with a scalar objective (agreement with human
gold labels), cheap experiments (one pass over a fixed gold set), and a large space of
plausible tweaks (prompt wording, decision order, anchors, context ablations, detector
thresholds) — precisely the regime where Karpathy's loop shines and where manual
iteration is slow and unprincipled. It is also **action item #1** on the current
PROJECT_STATE ("Improve judge calibration using gold labels…").

### The isomorphism

| karpathy/autoresearch | pixelAgent autoresearch (`autoResearch/`) |
|---|---|
| One GPU | One **frozen eval set**: gold-labeled first-failure steps (hash-pinned) |
| `prepare.py` (frozen) | `src/auto_research/objective.py` + frozen eval set + scoring — never mutated by the loop |
| `train.py` (one mutable file) | **One mutable candidate file**: `candidate.yaml` — detector thresholds + judge prompt/protocol config |
| `program.md` | `autoResearch/program.md` — research directives for what to explore |
| 5-minute budget | One full pass over the eval set per experiment; live mode adds a **hard $ cap** (project's $25 gate) |
| `val_bpb` (scalar, vocab-independent) | **Macro-F1 over taxonomy leaves** (multi-label, prediction vs adjudicated gold) — macro makes scores comparable when the leaf mix changes |
| Keep/discard, reviewable diffs | Append-only `data/ledger.jsonl`; each experiment = one candidate YAML diff + score; best candidate snapshotted |

### Why judge calibration first (and not, e.g., agent training)

- Training-loop autoresearch (Karpathy's own domain) needs GPUs we schedule via
  Slurm with human approval — wrong first target for an autonomous loop.
- Literature/brainstorm auto-research agents (the "P3/later" idea already in
  PROJECT_STATE) have no scalar metric — they can't be steered by keep/discard.
- Judge calibration has: existing infra (`cua_failure_analysis`), a decided protocol
  update to implement (meeting 2026-08-07 Decision 5: multi-label "all applicable"
  judging with reference trajectory + evaluator output), human gold labels arriving
  from the inter-annotator study, and a metric everyone already agreed to care about
  (per-leaf κ / judge-vs-human agreement).

## 3. Decomposition for pixelAgent

**Frozen (the loop must never modify):**
- The 16-leaf taxonomy (`errorAnalysis/failureTaxonomy.md` — frozen per root AGENTS.md).
- The eval set: traces + gold labels under `autoResearch/data/eval_set/`, pinned by
  SHA-256 in `eval_manifest.json`. The runner refuses to score against a modified set.
- The scoring code (`objective.py`): metric definitions change only by human PR.

**Mutable (the one artifact the loop edits):** a **candidate** YAML with two sections:
- `detectors:` — Tier-1 thresholds (`min_repeat`, `near_margin_ratio`, `far_threshold_px`,
  `long_horizon_threshold_ratio`, enable/disable + ordering of detectors).
- `judge:` — protocol version (v1 single-primary vs v2 multi-label per Decision 5),
  context ablation flags (reference trajectory? evaluator output? OSWorld score?
  k previous steps?), decision-order text, rule text, anchor file reference.

**Directives:** `autoResearch/program.md` — the standing instructions an agent
(Hermes/Claude/Cursor) reads before proposing candidates.

**Two executors, one interface:**
- `DetectorExecutor` — runs Tier-1 detectors on the eval set. **Fully offline,
  deterministic, free.** This is the P0 loop that runs today (in CI, on a laptop).
- `JudgeExecutor` — calls a VLM judge (vLLM OpenAI-compatible endpoint or Anthropic
  API via `ops/llm_client.py` conventions) with a cost meter and hard budget stop.
  P1; requires keys/cluster.

## 4. The metric (our `val_bpb`)

Primary scalar: **macro-F1 over taxonomy leaves**, computed multi-label
(prediction set = primary + secondary modes; gold set = adjudicated + secondary).
Reported alongside (never optimized directly): exact-set match, Jaccard, per-leaf
P/R/F1, primary-label accuracy, and Cohen's κ on primary labels.

Why macro-F1: with ≤16 leaves and skewed prevalence, micro-averaged or accuracy-style
metrics reward collapsing to the modal leaf; macro-F1 is per-leaf-fair the way
`val_bpb` is vocab-fair, and it degrades visibly if the candidate games one leaf.

**Anti-overfitting rules (the val/test discipline):**
1. Eval set splits into `calibration` and `holdout` at build time. Keep/discard uses
   **calibration only**; holdout is scored for every *kept* candidate and reported in
   the ledger, but the loop never branches on it.
2. A candidate that improves calibration but drops holdout by > ε is flagged
   `suspect_overfit` in the ledger.
3. Anchors must not quote eval-set traces (leakage rule; enforced by a check that
   anchor strings don't appear verbatim in eval traces).
4. With today's tiny gold sets (~10 traces), scores steer *engineering* choices only —
   no scientific claims until the gold set reaches protocol scale (150–200 steps).

## 5. Loop mechanics

```
read program.md + ledger tail
→ propose candidate (grid / queue file / LLM proposer)
→ hash candidate; skip if already tried
→ run executor over frozen eval set (budget-capped)
→ score vs gold (objective.py)
→ append ledger entry {candidate_hash, diff-vs-best, scores, cost, verdict}
→ keep if primary metric improves by ≥ min_delta, else discard
→ repeat until proposals exhausted / budget spent / max_experiments
```

Proposal sources, in rollout order:
- **P0 `grid`:** enumerated parameter grid from `config/proposals_*.yaml` (no LLM;
  deterministic; runs in this sandbox and CI).
- **P1 `queue`:** a human/agent-authored YAML queue of candidate edits — this is how
  Hermes or Claude sessions inject ideas asynchronously.
- **P2 `llm`:** an LLM proposer that reads `program.md` + ledger tail and emits the
  next candidate YAML (Anthropic via `ops/llm_client.py` conventions). Human approval
  gate on enabling it, per `docs/multi_idea_stages.md` roadmap ("Human approval gates
  stay until explicitly relaxed in root AGENTS.md").

## 6. Phased rollout & exit criteria (evals before builds)

| Phase | What | Exit criterion | Status |
|---|---|---|---|
| **P0** | Offline detector-calibration loop on synthetic fixture eval set; multi-label metrics; ledger | Loop runs end-to-end offline; kept candidate beats baseline on calibration *and* holdout; all tests green | **Shipped in this branch** |
| **P1** | Real gold labels (inter-annotator study output) become the eval set; `JudgeExecutor` against vLLM judge on Babel/Bridges; budget metering wired to the $25 gate | Judge macro-F1 measured on real gold; ≥1 kept prompt-config improvement replicated on holdout | Blocked on ~10-trace annotation ticket |
| **P2** | LLM proposer; overnight loop sessions (Hermes cron); candidate diffs surfaced in weekly report | ≥20 experiments/session unattended within budget; no guardrail violations | Needs Abdoul's approval |
| **P3** | Extend loop to second objective (e.g., Human-Agent instruction transformation — Raghav's track — success rate on a fixed task subset as the metric) | Scoping doc for objective #2 approved | Later |

## 7. Guardrails (non-negotiable, encoded in `autoResearch/AGENTS.md`)

- Never modify taxonomy, gold labels, eval set, or scoring logic from inside the loop.
- Never treat fixture-set scores as scientific results; fixtures validate the harness.
- Hard cost caps in live mode; default per-session cap $25 (Decision 3); the loop
  stops, it does not ask forgiveness.
- No GPU job submission from the loop without a human having approved the session
  (root AGENTS.md principle).
- Ledger is append-only; kept candidates never overwrite prior experiment artifacts.

## 8. Risks

- **Overfitting to a small gold set** — mitigated by split + suspect_overfit flag +
  scale discipline (§4); residual risk until 150–200-step gold set exists.
- **Metric gaming** (e.g., predicting every leaf to inflate recall) — macro-F1
  penalizes precision loss; exact-match and Jaccard reported as guard metrics.
- **Judge nondeterminism** — temperature 0, fixed seeds where the endpoint supports
  them, and n=2 repeat option for kept candidates.
- **Silent eval drift** — SHA-256 pinning of eval set; runner hard-fails on mismatch.
- **Scope creep** (loop starts editing pipeline code) — candidate schema is a closed
  parameter set; executors reject unknown keys.

## 9. Sources

- https://github.com/karpathy/autoresearch
- https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/
- https://kingy.ai/ai/autoresearch-karpathys-minimal-agent-loop-for-autonomous-llm-experimentation/
- https://kenhuangus.substack.com/p/exploring-andrej-karpathys-autoresearch
- https://www.verdent.ai/guides/what-is-autoresearch-karpathy
