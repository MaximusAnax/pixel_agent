# pixelAgent Compendium

The durable reference for this research program. Written to be read by a person
ramping up, or by an agent starting a session with no prior context.

**Compiled:** 2026-08-10, against `feat/continuing-failure-analysis` @ `4829e57`.
Sources: the Google Drive project folder (9 documents), this repo, and the SURA
report `PixelAgent_Research.pdf` (2026-08-03). Full inventory and re-pull
instructions: [`09-sources.md`](09-sources.md).

> **Relationship to other repo docs.** `ops/state/PROJECT_STATE.md` and the
> `PROJECT_STATE` block in root `AGENTS.md` are **auto-generated** — they answer
> "what happened recently," extractively, from dated meeting notes. This
> compendium is **hand-maintained and cumulative** — it answers "what is this
> project, what do we know, and why did we decide things this way," and it
> incorporates material (Drive docs, the SURA report, the literature review) that
> the automation never sees.
>
> **Frozen grounding docs win over both.** `failureTaxonomy.md`,
> `failureStudyProtocol.md`, `failureAnalysisFinalPlan.md`,
> `failureAnalysisPlan.md`, the stage `AGENTS.md`, and root `AGENTS.md` are frozen
> per [`errorAnalysis/docs/GROUNDING_MANIFEST.md`](../../errorAnalysis/docs/GROUNDING_MANIFEST.md)
> (2026-07-10, signed off by Abdoul). This compendium **describes** them; it never
> overrides them, and it must not be used to justify editing them.

---

## The project in one page

**Program.** Small vision-language models as computer-use agents (CUAs) operating
from pixels only. CMU, advised by **Prof. Matt Gormley**. Researcher: **Abdoul
Ndiongue**; collaborators **Raghav Gupta** and **Amaad Martin**.

**Ultimate deliverable.** A publishable, human-validated failure taxonomy with
quantitative prevalence on a stratified OSWorld subset.

**Current milestone — this is the thing to be precise about.** Per the 2026-07-10
Phase 0 freeze, the current milestone is **annotation-ready infrastructure**:
OSWorld task/eval context vendored, Human Agent screenshots available to both
annotators and the multimodal judge, a mockup-approved dual-trace review UI, and a
provisional `osworld_v1` rejudge. It is explicitly **not** judge calibration, not
prevalence CIs, and not paper figures. Those follow *after* human gold labels.

**Three-tier label model.** Keeping these apart is the core discipline of the
current phase:

| Tier | Artifact | Status |
|---|---|---|
| **Provisional judge** | versioned labels (`judge_context_version`, e.g. `osworld_v1`) | reference during discovery — **not** gold |
| **Human gold-in-progress** | `annotations.json` from `abdoul` / `raghav` | the scientific target |
| **Calibrated judge** | follow-on rejudge (e.g. `osworld_v2_gold_calibrated`) | used for scaled prevalence, later |

**Human reference is non-binding.** The OSWorld-Human sequence is *one viable
path*, not the only valid one. Do not require step-wise alignment to the agent
trace, and never label a failure solely because the agent diverged from the human
path. Prefer labeling an actual failure mode over "didn't match human."

**Where the research pressure is.** An OSWorld run guided by OSWorld-Human
reference steps, with UI-TARS-72B grounding, succeeded on only **60 of 361**
tasks — a run that should have approximated a ceiling. The other 301 surfaced
failures that are not about the model at all: incomplete OSWorld-Human step
instructions, actions fired before the screen finished loading, VMs that never
finished initializing. A judge calibrated on that data would learn to explain
benchmark bugs as reasoning errors. Hence: verify the evaluation pipeline first.

**Current empirical position.** `opencua_a3b_pilot30` covers **361 inventoried
episodes**; **16** are labeled by the Claude Sonnet 4.6 judge and queued for human
review (cost: **$0.26**). Zero adapter gaps on the OpenCUA A3B package. Reasoning
Drift + Goal Hallucination account for **75% of those 16** — provisional signal
only, pending gold calibration. **16/361 = 4.4% labeled is the headline blocker.**

---

## Contents

| # | File | Read it when |
|---|---|---|
| 1 | [`01-orientation.md`](01-orientation.md) | You are new. People, cadence, repo/Drive map, how the question got here. |
| 2 | [`02-research-program.md`](02-research-program.md) | You need the current thesis, the pipeline, and what is built vs. planned. |
| 3 | [`03-failure-taxonomy.md`](03-failure-taxonomy.md) | You are labeling, judging, or writing about failure modes. **Three versions exist in circulation — read this before citing any of them.** |
| 4 | [`04-evidence.md`](04-evidence.md) | You need a number. Every empirical result with its provenance and caveats. |
| 5 | [`05-literature.md`](05-literature.md) | You are writing related work or looking for prior art. |
| 6 | [`06-idea-bank.md`](06-idea-bank.md) | You are picking the next direction, or scoping a second idea/stage. |
| 7 | [`07-infrastructure.md`](07-infrastructure.md) | You are touching Babel, Bridges, vLLM, OSWorld, storage, or the labeling workflow. |
| 8 | [`08-decisions-and-questions.md`](08-decisions-and-questions.md) | You need the decision log, open questions, or known documentation drift. |
| 9 | [`09-sources.md`](09-sources.md) | You need to re-pull a source or check where a claim came from. |

Companion: [`docs/reviews/sura-report-review-2026-08-10.md`](../reviews/sura-report-review-2026-08-10.md)
— outstanding review items on the SURA report.

---

## Maintaining this

Update when something **durable** changes — a decision, a taxonomy revision, a
result, a direction that opens or closes. Do not mirror the weekly report here;
that is what `ops/reports/` is for.

- Record the base commit at the top when you revise. A compendium compiled against
  a stale branch is worse than none — that happened on the first pass.
- Keep the "one page" section true. If it goes stale, the rest stops being trusted.
- Re-pull Drive sources: see [`09-sources.md`](09-sources.md).
- **Never** edit a file listed in `GROUNDING_MANIFEST.md`. That includes both
  `AGENTS.md` files and all four `errorAnalysis` plan/taxonomy docs. Taxonomy leaf
  additions are deferred unless Abdoul requests them, and revisions come from
  **human discovery labels** — never from provisional judge disagreement alone.

---

## Freeze exception on record — root `AGENTS.md` pointer

`AGENTS.md` at the repo root is a frozen grounding doc
([`GROUNDING_MANIFEST.md`](../../errorAnalysis/docs/GROUNDING_MANIFEST.md),
2026-07-10). Two edits were made to it to make this compendium discoverable — a
"Start here" section above the `PROJECT_STATE` block, and a `docs/compendium/` row
in the Structure table.

| Field | Value |
|---|---|
| **Approved by** | Abdoul |
| **Date** | 2026-08-10 |
| **Scope** | Root `AGENTS.md` only — the two edits above, both outside the managed `PROJECT_STATE` block |
| **Rationale** | Without a pointer, a fresh Hermes or Claude session cannot find the compendium; discoverability is the whole point of writing it |

No other frozen file was touched. This exception does not generalize — any further
edit to a manifest-listed file needs its own approval.
