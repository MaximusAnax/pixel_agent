# 8 — Decisions, questions, and known drift

## Decision log

Standing decisions. Each holds until explicitly revisited.

> **On the dates.** `2026-06-24` and `2026-07-10` are the two dated meeting
> folders in `ops/meetings/`. A `2026-06-26` folder existed briefly and was
> **deleted upstream** — it was a pull-date artifact, not a meeting (see
> [`01-orientation.md`](01-orientation.md)). Decisions marked "later meeting"
> come from undated sections of the rolling Google Doc and cannot be dated.

### 2026-07-10 — Phase 0 grounding freeze

| # | Decision |
|---|---|
| 1 | **Current milestone = annotation-ready infrastructure** — OSWorld task/eval context, Human Agent screenshots for annotators + multimodal judge, mockup-approved dual-trace UI, provisional rejudge `osworld_v1`. **Not** judge calibration or publication prevalence |
| 2 | **Provisional judge vs human gold** — versioned judge labels (`judge_context_version`) are reference only; `annotations.json` from abdoul/raghav is gold-in-progress |
| 3 | **Human reference is non-binding** — full human sequence (text + screenshots) for context; do not overfit; **no forced step alignment to agent path** |
| 4 | **Rejudge waits for Human Agent** — multimodal `osworld_v1` only after `oracle_status` is ready/partial |
| 5 | **Grounding freeze** — files listed in `errorAnalysis/docs/GROUNDING_MANIFEST.md` must not be edited without a new approved plan |
| 6 | **UI mockup before production** — static HTML mockups approved before Jinja/packet implementation |

Also encoded in `failureTaxonomy.md` at the freeze:

- Human annotators write gold-in-progress to `annotations.json`; the VLM judge
  writes versioned provisional labels. **Do not revise the taxonomy from
  provisional judge disagreement alone.**
- Executed-action vs CoT `model_code` divergence (after coordinate normalization)
  is **evidence** for grounding leaves — **not** a new leaf.
- `evaluator_mismatch` broadened: use when eval criteria appear met, or the
  failure is an evaluator artifact rather than an agent mistake.

### Late June (2026-06-24 and undated sections)

| # | Decision | Notes |
|---|---|---|
| 7 | **All OSWorld VMs and inference on Babel / Bridges-2** — not local, not AWS | Supersedes the master plan's Option B/C language |
| 8 | **Bridges vLLM standard: 0.11.0, Python 3.11 conda env, `module load cuda/12.6.1`** | Resolves the CUDA 13 / libcudart failure |
| 9 | **Frontier-model cost gate: ≤ $25 → proceed; > $25 → check with Matt first** | Estimate from token counts before running |
| 10 | **Start from existing HuggingFace pre-generated trajectories** | — |
| 11 | **Focus models: OpenCUA, Kimi, Sonnet 4.5+** — not older models | — |
| 12 | **Different models for agent and judge** | Originally Qwen3.5-VL 0.8B / 9B; **now OpenCUA A3B/7B agent + `claude-sonnet-4-6` judge** (commit `ebfb470`) |
| 13 | **Serve OpenCUA with vLLM** | — |
| 14 | **All-applicable labeling** — annotators and judge select *every* applicable failure mode at `t*`, not one primary + optional secondaries | ✅ **Ratified 2026-08-10 (Abdoul).** Frozen `failureTaxonomy.md` still says one-primary; migration checklist in [`03-failure-taxonomy.md`](03-failure-taxonomy.md) |
| 15 | **Both annotators label the same pilot set independently** | Independence is the point |
| 16 | **Pilot gold-label criteria**: HumanAgent succeeded ∧ A3B failed ∧ 7B failed ∧ judge produced a conclusion | Isolates cases where diagnosis is meaningful |
| 17 | **Consolidate the two HTML annotation viewers into one** | Done |
| 18 | **Compute scope: 100 stratified tasks × 3 seeds × 2–3 models (~15k agent-steps), Pass@3** | Explicitly **not** 369×10 unless reliability becomes its own RQ |
| 19 | **OpenTau is not used** | Robotics VLA training, not relevant |

---

## Open questions

### Blocking the current milestone

- **Human Agent completion.** The `osworld_v1` rejudge is gated on `oracle_status`
  reaching ready/partial. This is the critical path.
- **Throughput.** 16 of 361 episodes labeled (4.4%). Scaling labeling throughput is
  named in the weekly report as the immediate next milestone before any result can
  be called representative.
- ~~One primary label, or all-applicable?~~ **Settled 2026-08-10: all-applicable.**
  Now an implementation task, not an open question — but the 7-row migration
  checklist in [`03-failure-taxonomy.md`](03-failure-taxonomy.md) must be finished
  **before** the discovery labeling batch. Two items in it produce silently wrong
  numbers rather than errors (`per_leaf_kappa` and `judge_vs_human_agreement` both
  still assume a single label per record).
- **Is `modes_ordered` position meaningful?** `review/labels.py` exports
  `modes_ordered[0]` as each annotator's `_primary`. Under all-applicable, either
  that order is a deliberate rank (tell annotators) or it is click order (stop
  exporting a primary from it).

### Research-blocking

- **Is the 60/361 gap fixable, and how much is benchmark vs. model?** Until this is
  decomposed, no prevalence number means anything.
- **How do we rewrite under-specified OSWorld-Human instructions** (adding "press
  Enter" and similar)? Literature reports instruction clarification swinging results
  0% → 100%.
- **Why do OSWorld initialization bugs occur** — why is Chrome not open on setup?
  Can hanging tasks be detected and excluded automatically?
- **369 vs 361.** OSWorld has 369 tasks; the guided run and the pilot inventory both
  report 361. Reconcile before publishing either number.
- **Taxonomy: 2 categories / 16 leaves, or 3 / 19?** The SURA report and EOS use a
  three-category version that also drops two leaves. Leaf additions are deferred
  unless Abdoul requests them, and revisions should come from discovery labels. See
  [`03-failure-taxonomy.md`](03-failure-taxonomy.md).
- **How should failure modes be prioritized** — step of occurrence, downstream
  impact, or a deliberately designed function?

### Scientific

- **Do CUAs perform worse when given screenshot context, and if so why?** Never
  tested directly; keeps recurring in notes. A clean, cheap ablation.
- **Are Qwen-class CUA models trained to understand frame *sequences*** at all, or
  only single frames?
- **SOTA for small models (≤3B)** on GUI grounding? On pixel-based computer use
  (OSWorld-Verified)?
- **What counts as "small"** — 1B, 2B, 4B, 7B? Unresolved since May.
- **Open-weights (Qwen) vs. fully-open-source (Molmo)** — does the distinction
  matter for the contribution?
- **Is OSWorld still the right benchmark?** Frontier models are evaluated on OSWorld
  **v2.0**. Alternatives: TheAgentCompany, WebArena, OSWorld-Verified.
- **Is failure analysis only relevant to small models**, if frontier models make few
  errors?
- **Beyond scrolling, what scenarios genuinely require temporal context?**
- **Is there value in letting a pixel-only agent use code (CodeAct-style)?** Asked
  repeatedly; never answered with concrete use cases.

---

## Action items

> **2026-08-10 cleanup (Abdoul):** every June carry-over item below that is not
> part of the current milestone was ruled **dead** — SSH key + cron monitoring,
> Babel/Bridges guide write-ups, the 3-paper-ideas assignment, SURA
> re-application, `Skill.md`, and the trajectory data-format item (superseded by
> the packet + `annotations.json`). "Sign off Phase 0" was already done
> (manifest, 2026-07-10). Live work is tracked in
> [`docs/tickets/BACKLOG.md`](../tickets/BACKLOG.md).

**Abdoul**
- ~~Sign off Phase 0 / `GROUNDING_MANIFEST.md`~~ ✅ done 2026-07-10
- After sign-off, start the post–Phase 0 plan: vendor metadata → mockups → Human
  Agent → `osworld_v1`
- Compute the frontier-model token cost estimate; apply the $25 gate
  (`scripts/estimate_judge_cost.py` exists)
- Document the lab-standard Bridges env and share with the team
- SSH key for Babel/Bridges usable by the Hermes agent; cron jobs to monitor experiments
- SURA re-application

**Abdoul + Raghav**
- Discovery labeling on the annotation-ready pilot packet (after infrastructure)
- Then: agreement diagnostics, discuss disagreements, propose taxonomy revisions
  *(taxonomy edits require Abdoul's approval — frozen doc)*

**Raghav**
- Finish Human Agent / human-trajectory screenshots, merge into the repo
- Method for transforming human trajectories into more accurate instructions that
  raise the human-agent success rate
- Diagnose OSWorld initialization bugs / hanging states
- Read further into failure-analysis papers for alternative categorization schemes

**Amaad**
- Dataset not in Qwen's training data for grounding differentiation; synthetic data
  gen / augmentation from paired screenshot + HTML

**Everyone** — 3 paper ideas each *(Amaad's and Raghav's are captured in
[`06-idea-bank.md`](06-idea-bank.md))*

---

## Known drift

Checked 2026-08-10 against `feat/continuing-failure-analysis` @ `4829e57`.

### Resolved since the first compendium pass ✅

The Phase 0 freeze fixed most of what the earlier draft flagged:

- `failureAnalysisFinalPlan.md` → **v1.1**: current milestone stated, provisional-vs-
  gold table added, immediate-next-steps rewritten, timeline updated.
- `failureStudyProtocol.md`: judge input bundle rewritten with the full context
  requirement, trace step semantics added, human-reference contract added.
- `failureTaxonomy.md`: annotator-vs-judge boundaries added, `evaluator_mismatch`
  broadened.
- `ops/meetings/2026-06-26/` **deleted** — the phantom meeting is gone.
- `ops/reports/W27–W29` deleted, `W26` rewritten narrative-first.
- `PROJECT_STATE.md` regenerated as of 2026-07-10.
- Root `AGENTS.md` now carries the grounding-freeze pointer and the mattlab shared
  storage boundary.

### Still outstanding ⬜

| Artifact | Problem |
|---|---|
| **SURA report** (`PixelAgent_Research.pdf`) | Diverges from the **frozen** taxonomy: uses 3 categories / 14 model leaves vs. the frozen 2 / 16, dropping Hidden Operation Blindness and Cross-Application Context Loss. Also frames the judge as reference-*bound* when the frozen protocol says non-binding. Full list: [`docs/reviews/sura-report-review-2026-08-10.md`](../reviews/sura-report-review-2026-08-10.md) |
| ~~One-primary vs all-applicable labeling~~ | ✅ Resolved 2026-08-10: policy ratified, code migrated, frozen taxonomy text updated via approved plan |
| ~~`failureStudyProtocol.md` model table~~ | ✅ Fixed 2026-08-10 via approved plan `docs/plans/2026-08-10-frozen-doc-corrections.md` |
| ~~`failureStudyProtocol.md` compute section~~ | ✅ Fixed 2026-08-10 via the same plan (vLLM 0.11.0; Babel provisioned/primary) |
| `errorAnalysis/data/prevalence.json`, `attributions.jsonl` | `n_failures: 1`. Plumbing tests, not results. Don't quote. |
| Rolling Google Doc | Sections remain **undated**, so `pull_gdoc_notes.py --section-only` still cannot split meetings after 2026-07-10. |

### The highest-leverage fix

**Date each section in the rolling Google Doc.** The ops loop is healthy but
starved of parseable input — that is why the meeting record has only two dated
folders while the Doc runs current to 2026-08-07, and why a phantom `2026-06-26`
folder had to be deleted by hand.

### A note on the frozen files

Three of the outstanding items live inside frozen grounding docs. That is not a bug
in the freeze — the freeze is doing its job. But it means these corrections need to
be batched into the **next approved plan** rather than fixed opportunistically.
Worth putting on the agenda explicitly so they do not quietly rot.
