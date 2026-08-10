# 1 — Orientation

## People

| Person | Role | Handles |
|---|---|---|
| **Abdoul Ndiongue** | Researcher (SURA). Owns judge build/prompt design, error-analysis pipeline, ops automation. | `andiongu@andrew.cmu.edu` · GitHub `MaximusAnax` · Babel `andiongu` · Bridges `andiongue` |
| **Prof. Matt Gormley** | Advisor. Approval gate for scope, cost, and taxonomy changes. | GitHub `mgormley` |
| **Raghav Gupta** | Collaborator. Owns OSWorld-Human integration, oracle agent, grounding-benchmark reproduction, second annotator. | `raghavgupta@cmu.edu` · GitHub `Raghav3003` · Bridges `rgupta19` |
| **Amaad Martin** | Collaborator. Grounding/data-differentiation angle, benchmark landscape, storage guidance. | GitHub `Amaadmartin` |

Both Abdoul and Raghav annotate the pilot set independently — that independence is
the whole point of the calibration design, so it must be preserved.

## Cadence

- **Weekly full-team meeting** (Abdoul + Raghav + Amaad + Matt), notes in the
  rolling Google Doc. Configured meeting window in `ops/config/meetings.env`: 11:00–12:30.
- **Separate Abdoul + Raghav working sessions** — captured in the doc's second tab.
- **Friday** — `ops/weekly_report.py` runs in CI, drafts `ops/reports/<week>.md`.
- **After each meeting** — `pull_gdoc_notes.py` → `synthesize_state.py` regenerates
  `PROJECT_STATE.md` and the managed block in root `AGENTS.md`.

Full loop: [`docs/meeting_notes_workflow.md`](../meeting_notes_workflow.md),
[`docs/project_state_automation.md`](../project_state_automation.md).

## Where things live

**Repo** — `github.com/MaximusAnax/pixel_agent`

```
AGENTS.md                    root context; contains auto-generated PROJECT_STATE block
docs/compendium/             ← you are here
docs/                        workflow + automation docs, multi-idea stage checklist
ops/                         weekly report, gdoc ingest, state synthesis, meetings/, reports/
errorAnalysis/               Phase 1 stage — the failure-analysis pipeline
  failureAnalysisFinalPlan.md   master plan v1.0
  failureStudyProtocol.md       phases A–E methodology
  failureTaxonomy.md            FROZEN 16-leaf taxonomy + decision rules
  failureAnalysisPlan.md        experiment design
  src/cua_failure_analysis/     package: detectors, attribution, judge, labeling, stats
  scripts/babel/, scripts/bridges/   cluster runbooks
hermes/skills/               agent skills (project-state-sync)
```

**Google Drive** — the project folder holds the human-authored thinking that never
made it into the repo. Four subfolders:

- root — rolling meeting notes doc (2 tabs), SURA EOS Report
- `Failure Mode Analysis/` — taxonomy v1, stress-test experiment plan, mitigation
  strategies, the OSWorld-Human literature report
- `Ideation/` — Research Ideation Tracker, Visual Trajectory Steering proposal
- `Literature/` — Reading List, Memory Inception implications

Exact IDs and re-pull commands: [`09-sources.md`](09-sources.md).

## How the research question got here

This project has narrowed three times. Each narrowing was driven by finding out
the previous framing rested on something unverified. That pattern is the most
important thing to understand about the work.

| When | Framing | What broke it |
|---|---|---|
| **Mid-May 2026** | "Small VLMs for pixel-only computer use." Open questions were definitional: what counts as *small*? do we care about open-weight (Qwen) vs. fully-open-source (Molmo)? | Too broad to act on. Nobody knew where small models actually fail. |
| **Late May** | Read into it — SeeClick, OSWorld, Qwen2-VL, Qwen3-VL. Amaad surfaced the stat that reframed everything: **icon grounding accuracy 21–72%, text grounding 70–82%**. | Concluded grounding, not planning, is the small-model bottleneck — but that was inference from benchmark aggregates, not from observed failures. |
| **Early–mid June** | "Before fixing small models, understand *how* they fail." Error-analysis pipeline: pull OpenCUA trajectories from HuggingFace, use a second model as judge to explain each failure. Taxonomy drafted (perception/grounding vs. cognitive/planning). | The judge had nothing to compare against. A failed trace alone underdetermines *why* it failed. |
| **Early July** | Found **OSWorld-Human** — human-validated correct steps for all 369 OSWorld tasks. Sharpened to: give the judge the agent trace *and* the human trace, ask it to select every applicable failure mode. | Needed screenshots per human step, not just text → requires an oracle agent replaying human actions inside OpenCUA. |
| **Late July → now** | Ran it. **60/361.** A meaningful share of "failures" were benchmark artifacts, not model errors. | Current framing: **build a verified evaluation pipeline before calibrating the judge.** Benchmark/environment artifact became a first-class failure category. |

Abdoul's own summary, from the EOS report: *"Every time I thought we'd found the
real problem, there was another layer underneath it: model capability, then
grounding vs. planning, then benchmark data quality, then environment reliability."*

## Timeline of artifacts

| Date | Event |
|---|---|
| 2026-05-20 | Meeting notes doc + Reading List created |
| 2026-06-12 | Failure Mode Analysis + Literature folders populated: taxonomy v1, stress-test plan, mitigation strategies, Memory Inception implications, VTS proposal |
| 2026-06-19 | Ideation folder + Research Ideation Tracker |
| 2026-06-24 | **Team meeting** (only dated June meeting). Bridges vLLM/CUDA blocker resolved (vLLM 0.11.0) |
| 2026-06-26 | Pilot v4 runs: `20260626_172919_a3b_pilot_full_v4`, `20260626_172922_7b_pilot_full_v4`. PRs #1 and #2 merged — Babel HF orchestration + Hermes setup, and ops/state automation |
| 2026-07-03 | OSWorld-Human literature report written. Pilot review packet `pilot_taxonomy_paired_20260703` built |
| 2026-07-10 | **Phase 0 grounding freeze.** Async planning session: annotation-ready milestone defined, provisional-vs-gold split, human reference declared non-binding, `GROUNDING_MANIFEST.md` signed off |
| Jul (through `4829e57`) | Trace review UI, multi-annotator annotations, mattlab shared Babel root, Anthropic judge (`claude-sonnet-4-6`), A3B adapter + Tier-1 attribution, OSWorld context vendoring |
| 2026-07-30 | SURA End-of-Summer Report written |
| 2026-08-03 | SURA Report (`PixelAgent_Research.pdf`) dated |
| 2026-08-07 | **Team meeting** — CI post-meeting sync captured it on `main` (`430d6ae`); folded into PROJECT_STATE at the 2026-08-10 merge |

> ⚠️ **On meeting dates.** The Google Doc has **no dated sections** — every section
> header carries a blank "Attendees:" line — so `pull_gdoc_notes.py --section-only`
> has nothing to split on. A `ops/meetings/2026-06-26/` folder briefly existed and
> was **deleted upstream**: it was named for the *pull date*, its `gdoc_notes.md`
> was a dump of the entire rolling Doc rather than one meeting's section, and its
> `notes.md` was a near-duplicate of the 2026-06-24 one — the same source text
> summarized twice and presented as two meetings. (The `2026-06-24` folder's own
> header says it was pulled *on 2026-06-25*, so treat even that date loosely.)
>
> Dated meeting folders: **2026-06-24**, **2026-07-10**, and **2026-08-07** (the
> last arrived via the CI post-meeting sync on `main`, merged 2026-08-10).
> Sections between those dates remain unattributable.
> Statements from those sections are cited here as "a later meeting" or "the most
> recent meeting." Dating the Doc's sections would repair the meeting record,
> `PROJECT_STATE.md`, and this timeline in one pass — see
> [`08-decisions-and-questions.md`](08-decisions-and-questions.md).

> **Do not read `ops/reports/` as a progress signal.** The July weekly reports
> recorded zero commits and zero new experiment runs, while in reality that window
> produced the trace review UI, the multi-annotator workflow, the Anthropic judge
> integration, the A3B adapter, and the Phase 0 freeze — 205 files and ~19k
> insertions on `feat/continuing-failure-analysis`. The automation counts commits
> on the branch it is pointed at; this project's real work often lands elsewhere,
> or is not a commit at all.

## Project-wide principles

From root `AGENTS.md`, and they hold across every stage:

- Evidence over confident guesses. Separate **raw evidence**, **attribution**, and
  **interpretation**; flag uncalibrated interpretation as provisional.
- Prefer remote/cluster computation over hoarding large data locally.
- Produce small, inspectable artifacts over raw-data piles.
- Favor fast calibration loops over premature large sweeps.
- No large/expensive GPU jobs without Abdoul approving the reason.
- Never overwrite prior results; never change a stage's core definitions
  (taxonomies, protocols) without explicit approval.
