# Plan: frozen-doc corrections batch (PXA-004)

**Status: APPROVED and APPLIED (Abdoul, 2026-08-10).** Per
`errorAnalysis/docs/GROUNDING_MANIFEST.md`, the files below are frozen; this
document is the "new approved plan" the manifest requires before they change.
Applied in one commit on `claude/pixelagent-research-compendium-9aaa86` referencing this plan.

Scope: four factual corrections. No leaf additions, no methodology changes —
those wait for discovery-label evidence.

---

## Edit 1 — `errorAnalysis/failureTaxonomy.md`: labeling policy → all-applicable

Ratified by Abdoul 2026-08-10. Replace, under **Labeling policy → Scope**:

**Before**
> - Assign exactly **one primary** root-cause leaf per `t*`.
> - Optionally assign **secondary** leaves when multiple modes clearly co-occur at the same step.

**After**
> - Assign **every applicable leaf** at `t*` as an ordered list
>   (`modes_ordered`), **most-central-first** — the root-cause mode first.
>   One leaf is a valid answer when only one applies; do not pad.
> - The first element plays the role the earlier policy called "primary"; tooling
>   may derive a primary from position 0 for backward compatibility.

And in the **Global decision order** heading, add one clarifying line:

> This order disambiguates confusable pairs and identifies the most central
> mode; it does **not** limit how many leaves may be assigned.

## Edit 2 — model tables in `failureStudyProtocol.md` and `failureAnalysisFinalPlan.md`

Both tables still name the June draft pair. Replace rows:

| Role | Was | Now |
|---|---|---|
| Agent(s) under analysis | Qwen3.5-VL-0.8B (ultra-small), OpenCUA-7B | **OpenCUA A3B and OpenCUA-7B** (HF pre-generated trajectories; paired pilot) |
| Judge (draft/provisional) | Qwen3.5-VL-9B+ via vLLM | **`claude-sonnet-4-6`** (Anthropic API; provisional labels versioned via `judge_context_version`) |
| Judge (validation) | Frontier API or ≥32B | unchanged — calibration against human gold in Phase D |

## Edit 3 — `failureStudyProtocol.md` compute section

- `pip install 'vllm>=0.12.0'` → **`pip install vllm==0.11.0`** with a note:
  0.12.0+/0.23 wheels are built against CUDA 13 and fail on Bridges' CUDA 12.6
  (`libcudart.so.13` ImportError). Standard: vLLM 0.11.0, Python 3.11 conda env,
  `module load cuda/12.6.1`.
- "CMU Babel (secondary — pending): Account not yet provisioned" → **Babel is
  provisioned and is the primary cluster for HF trajectory analysis**; shared lab
  tree at `/data/group_data/mattlab/pixel_agent/`. Bridges remains for vLLM
  serving work.

## Edit 4 — `failureStudyProtocol.md` + `failureAnalysisFinalPlan.md` judge output schema

Where the judge output is specified as
`{primary_mode, secondary_modes[], propagated, t_star, tier_used, confidence}`,
update to:

`{modes_ordered[], propagated, meta_labels[], t_star, tier_used, evidence_cot_span, confidence}`

with a compatibility note: `primary_mode`/`secondary_modes` are retained as
derived fields (`primary_mode == modes_ordered[0]`) so earlier records remain
loadable. *(The code already works this way as of the PXA-002 commit.)*

## Edit 5 — `errorAnalysis/docs/GROUNDING_MANIFEST.md` sign-off section

Append two lines to the sign-off list:

> - [x] **Exception (Abdoul, 2026-08-10):** root `AGENTS.md` — compendium
>   pointer ("Start here" section + Structure table row), outside the managed
>   `PROJECT_STATE` block.
> - [x] **Amendment (Abdoul, YYYY-MM-DD):** this corrections batch
>   (`docs/plans/2026-08-10-frozen-doc-corrections.md`) applied.

---

## Explicitly out of scope

- Benchmark/environment-artifact category (3-category / 19-leaf question) —
  waits for discovery-label evidence per the freeze decision.
- Any new leaf, decision rule, or controlled-track change.
- The SURA report (tracked separately in `docs/reviews/`).

## Sign-off

- [x] **Abdoul** approved the five edits (2026-08-10, in session); applied in a
  single commit referencing this plan.
