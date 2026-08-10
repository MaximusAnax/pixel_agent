# program.md — research directives for the autoresearch loop

(The analog of karpathy/autoresearch's `program.md`: standing instructions any
proposal agent — Hermes, Claude, Cursor, or the P2 LLM proposer — reads before
proposing candidates. Humans edit this file; the loop only reads it.)

## Objective

Maximize multi-label **macro-F1 between the attribution pipeline and gold
failure labels** on the calibration split of the pinned eval set. Holdout is
reported to you in the ledger but you must never tune against it. Guard
metrics (exact-match, Jaccard, per-leaf F1) should not collapse while
macro-F1 rises — a candidate that games one leaf is a regression.

## Current priorities (edit as the project moves)

1. **Detector thresholds** (free, offline): min_repeat, near-margin vs
   far-threshold interplay, long-horizon threshold ratio. The known tension:
   widening `near_margin_ratio` fixes medium click misses, but shrinking
   `far_threshold_px` instead relabels them Location Hallucination (wrong).
2. **Judge protocol v2 ablations** (Decision 5, needs judge endpoint): does
   the reference trajectory help or distract? Does the evaluator output make
   the judge lazy (guard: per-leaf recall on perception leaves)? Does
   `prev_steps_k` > 3 improve looping/memory leaves?
3. **Screenshot ablation**: `include_screenshot: false` tests the open
   question "do CUAs (as judges) do worse with screenshot context?" — the
   2026-08 SOTA scan found no published failure-category-level ablation of
   screenshot vs action-history context; a clean result here is novel.
4. **Decision-order text**: reorderings of the tie-break rules in the system
   prompt (judge executor, `decision_order` field).

## Rules for proposals

- Change at most 2 parameters per candidate; name the hypothesis in `notes`.
- Never propose values outside the schema bounds (candidates.py validates).
- Prefer experiments that discriminate between hypotheses over pure sweeps.
- When the ledger shows a plateau (10+ discards in a row), switch parameter
  family rather than shrinking step sizes.

## Standing cautions

- Eval set is synthetic fixtures until the human gold set lands — treat
  scores as harness signal, not science.
- Budget: $25/session hard cap on judge runs (Decision 3).
