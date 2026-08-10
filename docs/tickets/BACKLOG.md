# pixelAgent backlog

Ticket-style action items, compiled 2026-08-10 from the compendium, the Phase 0
freeze, the 2026-07-10 meeting, the SURA report review, and repo state. No
ticketing system exists yet — this file is the system. IDs are stable; strike a
ticket rather than deleting it.

**Priorities:** P0 = on the critical path to discovery labeling, or a data-loss
risk · P1 = needed this phase · P2 = hygiene, do soon · P3 = conditional/optional.
**Effort:** XS < 30 min · S = 0.5–2 h · M = half-day–2 days · L = multi-day.

**Status codes:** `open` · `needs-decision` · `blocked(<ids>)` · `done`

---

## Critical path — the dependency spine

```
PXA-002 (judge prompt) ──┐
PXA-005 (Human Agent)  ──┼→ PXA-007 (osworld_v1 rejudge) → PXA-008 (packet rebuild) → PXA-009 (discovery labeling) → PXA-010 (agreement)
PXA-006 (cost gate)    ──┘                                        ↑                          ↑
PXA-003 (modes_ordered ruling) ───────────────────────────────────┘                          │
PXA-021 (hide judge labels)    ───────────────────────────────────┘                          │
PXA-001 (agreement.py fix) ──────────────────────────────────────────────────────────────────┘
```

---

## Epic 0 — Protect work in flight

### PXA-000 — Commit or stash the 23-file WIP in the main checkout
**P0 · XS · Owner: Claude · Status: done (2026-08-10)**

> ✅ Committed as `2a0ebb5` "wip: oracle->handoff refactor in flight" on
> `feat/continuing-failure-analysis` (tracked changes + new test; .DS_Store junk
> excluded). Amend or split as you like.

The main checkout has 23 modified/deleted files uncommitted (oracle→handoff
refactor: `oracle/` modules and `audit_human_actions.py` deleted, review/packet
pipeline touched, new `test_oracle_handoff.py` untracked). Today the entire
project folder disappeared from disk for ~15 minutes; only the git remote made
that a non-event. Uncommitted work has no such protection.

**AC:** WIP committed (even as `wip:` commit) or stashed with a label; pushed
somewhere off-machine.

---

## Epic A — All-applicable label migration

Ratified 2026-08-10. Everything here must land **before PXA-009**, or agreement
numbers will be silently wrong.

### PXA-001 — Fix agreement metrics for multi-label
**P0 · S · Owner: Claude · Status: done (2026-08-10) · Blocks: PXA-010**

> ✅ Done: `agreement.py` rewritten — membership-based per-leaf κ, exact-set-match,
> mean Jaccard, set-level κ (reduces to old behavior on singletons); back-compat
> for bare-string labels; multi-label regression tests added. 67 tests pass.

`labeling/agreement.py` assumes one label per record. `per_leaf_kappa` uses
equality (`r.get(annotator) == leaf`) — under multi-label it measures only one
label and errors never surface. `judge_vs_human_agreement` does exact single-label
equality.

**Scope:** records carry mode *lists*; `per_leaf_kappa` uses set membership
(`leaf in modes`) for one-vs-rest binary κ; `judge_vs_human_agreement` reports
per-leaf binary agreement plus a set-level metric (exact-set-match and Jaccard);
extend `tests/test_agreement.py` with multi-label fixtures.

**AC:** no code path compares whole label sets by string equality; multi-label
fixtures pass; κ ≥ 0.6 target semantics documented as per-leaf presence/absence.

### PXA-002 — Rewrite judge prompt + output schema for all-applicable
**P0 · S–M · Owner: Claude · Status: done (2026-08-10) · Blocks: PXA-007**

> ✅ Done: prompt asks for `modes_ordered` (all applicable, most-central-first);
> decision order reframed as disambiguation; `AttributionResult` gains
> `modes_ordered` with two-way sync to legacy primary/secondary; both judge
> clients share `attribution_from_parsed` with legacy-response fallback;
> `labels.py::judge_modes_ordered` prefers the explicit list. Version note:
> `osworld_v1` has not run yet, so the rejudge is natively all-applicable —
> no extra `judge_context_version` bump required.

`judge/prompts.py:38` says "EXACTLY ONE primary label"; L61 "assign secondary
labels only if…"; output schema is `{primary_mode, secondary_modes[]}`.

**Scope:** prompt asks for *every applicable* mode; schema decision (recommend
`modes: []` + keep `propagated` bool — root-vs-downstream is already carried by
`propagated_failure`, so a separate primary slot is redundant); update parsing in
judge client / attribution pipeline / `review/labels.py::judge_modes_ordered` /
packet manifest; **bump `judge_context_version`** — the existing 16 provisional
labels were produced under one-primary and must not mix silently with new labels.

**AC:** prompt and schema consistent with the annotation format; parser validated;
version bumped; old outputs untouched (never overwrite).

### PXA-003 — Rule on `modes_ordered` semantics
**P0 · XS · Owner: Abdoul · Status: done (2026-08-10) · Blocks: PXA-008/009**

> ✅ Ruled: **deliberate rank, most-central-first.** Annotator instructions added
> to `trace_review_labeling.md` (Labeling policy section); `_primary` export from
> position 0 stays and is now documented.

The review UI stores human labels as an ordered list and `review/labels.py`
exports `modes_ordered[0]` as `<annotator>_primary`. Under all-applicable, either
(a) the order is a deliberate rank — then annotator instructions must say
"most-central-first" — or (b) it is click order — then stop exporting a primary
derived from it.

**Recommendation:** (a) documented rank. Costs one sentence of instructions,
keeps backward comparability with the 16 one-primary judge labels, and degrades
gracefully to (b) if annotators ignore it.

**AC:** ruling recorded in `trace_review_labeling.md`; annotator instructions
updated; export either documented or removed.

### PXA-004 — Approved-plan batch edit to the frozen docs
**P1 · S · Owner: Claude · Status: done (2026-08-10 — approved by Abdoul, applied)**

> Draft: [`docs/plans/2026-08-10-frozen-doc-corrections.md`](../plans/2026-08-10-frozen-doc-corrections.md)
> — five edits, incl. the judge-schema doc update and the manifest sign-off lines.

Four corrections are trapped behind the grounding freeze. Batch them into one
plan, one commit, one sign-off:

1. `failureTaxonomy.md` labeling policy: one-primary → all-applicable (2026-08-10 decision)
2. `failureStudyProtocol.md` + `failureAnalysisFinalPlan.md` model tables:
   agent = OpenCUA A3B/7B, judge = `claude-sonnet-4-6` (not Qwen3.5-VL 0.8B/9B)
3. `failureStudyProtocol.md`: `vllm>=0.12.0` → **0.11.0**; Babel "account not yet
   provisioned" → provisioned, primary cluster
4. `GROUNDING_MANIFEST.md` sign-off section: record the 2026-08-10 `AGENTS.md`
   freeze exception (compendium pointer)

**AC:** single commit touching only these; sign-off line added to the manifest;
compendium drift table updated to ✅.

---

## Epic B — Critical path to discovery labeling

### PXA-005 — Finish Human Agent (oracle) screenshots for the pilot set
**P0 · M–L · Owner: Raghav · Status: open (in progress) · Blocks: PXA-007**

The `osworld_v1` rejudge is gated on `oracle_status` ready/partial. Replay
OSWorld-Human actions per pilot task, capture per-step observation PNGs, write
`human_traj.json` + `grounding_cache.jsonl` under the mattlab tree.

**AC:** `oracle_status` ∈ {ready, partial} for the 30 pilot tasks; `failed` tasks
documented with reason (feeds PXA-011); artifacts on Babel shared tree.

### PXA-006 — Cost estimate for the enriched multimodal rejudge
**P1 · XS · Owner: Abdoul · Status: open · Blocks: PXA-007**

$0.26 covered 16 episodes *without* human screenshots. The enriched bundle (task
JSON + eval bundle + agent screenshots + full human sequence with images) is much
larger. Run `scripts/estimate_judge_cost.py` for the pilot scope; apply the $25
gate (≤ $25 proceed; > $25 check with Matt).

**AC:** number recorded (compendium 04-evidence); gate decision noted.

### PXA-007 — Run the provisional multimodal rejudge `osworld_v1`
**P0 · S · Owner: Abdoul · Status: blocked(PXA-002, 005, 006)**

Rejudge the pilot traces with the enriched bundle and the all-applicable prompt.
Version-tag outputs; never overwrite prior judge labels.

**AC:** versioned labels frozen into `packet_manifest.json`; provisional-only
status noted.

### PXA-008 — Rebuild pilot packet + annotator dry run
**P0 · S · Owner: Abdoul · Status: blocked(PXA-007, 003)**

Rebuild `pilot_taxonomy_paired_20260703` (or successor) with enriched context,
human column, `osworld_v1` labels. Then a 1-trace dry run: both annotators load
the UI, save a test label, verify Babel sync round-trip, then delete test labels.

**AC:** packet rebuilt; both annotators' test labels round-trip through
`annotations.json`; test labels removed.

### PXA-009 — Discovery labeling batch
**P0 · M · Owner: Abdoul + Raghav · Status: blocked(PXA-008; A-epic complete)**

The payload. 60 traces (30 tasks × A3B + 7B), labeled independently by both
annotators: all applicable modes + failing-step integer. No peeking at each
other's labels; judge labels hidden until save per PXA-021 (ruled 2026-08-10).

**AC:** both annotators complete on all 60; annotations synced; independence
preserved.

### PXA-010 — Agreement diagnostics + disagreement review
**P1 · S · Owner: Abdoul · Status: blocked(PXA-001, 009)**

Per-leaf κ human↔human and human↔judge; catalogue disagreements; draft taxonomy
revision proposals (this is where the 3-category / benchmark-artifact question
gets its evidence). Proposals go to Abdoul for the next approved plan — not edits.

**AC:** per-leaf κ table; disagreement catalogue; written revision proposals.

---

## Epic C — Benchmark validity

### PXA-011 — Diagnose OSWorld VM initialization failures
**P1 · M · Owner: Raghav · Status: open**

Why is Chrome not open on setup? Which tasks hang? Produce either an automatic
detector (flag contaminated episodes) or an exclusion list consumed by the
pipeline, so init failures stop polluting labels.

**AC:** root causes documented; detector flag or exclusion list wired in.

### PXA-012 — Instruction-repair method for OSWorld-Human
**P1 · M · Owner: Raghav · Status: open**

Transform human trajectories into complete instructions (add the missing "press
Enter" class of steps). Literature reports 0%→100% swings from instruction
clarification. Validate on a small set: human-agent success before vs. after.

**AC:** method documented; before/after success measured on ≥10 tasks.

### PXA-013 — Reconcile 369 vs 361
**P2 · XS–S · Owner: Abdoul · Status: open**

OSWorld has 369 tasks; both the guided run and the pilot inventory report 361 —
systematic exclusion, not a typo. Identify the 8 task IDs and why they drop.

**AC:** 8 IDs + reason documented in compendium 04-evidence.

### PXA-014 — Record the grounding-reproduction model family
**P2 · XS · Owner: Raghav · Status: open**

The 7B/32B ScreenSpot V2 / OSWorld-G reproduction rows name no model family in
any source. Needed before those numbers appear in a paper.

**AC:** model IDs recorded beside the numbers (meeting doc + compendium).

---

## Epic D — Ops & docs hygiene

### PXA-015 — Date the sections in the rolling Google Doc, then re-pull
**P1 · XS · Owner: Abdoul · Status: open — highest leverage per unit effort**

The Doc has no dated sections, so `pull_gdoc_notes.py --section-only` cannot
split meetings; everything after 2026-07-10 is unattributable and PROJECT_STATE
starves. Add a date heading per meeting section (both tabs), re-pull, re-run
`synthesize_state.py`.

**AC:** dated `ops/meetings/<date>/` folders exist for post-07-10 meetings;
PROJECT_STATE "most recent meeting" is current.

### PXA-016 — Verify `pull_gdoc_notes.py` reads Doc *tabs*
**P2 · XS · Owner: Claude · Status: done (2026-08-10)**

> ✅ Confirmed bug and fixed: `fetch_doc_text` now passes `includeTabsContent=True`,
> walks all tabs (with `## Tab:` headers), and — a second latent bug — extracts
> **table** content, which the meeting doc uses for its entire layout. Next real
> pull (PXA-015) validates end-to-end.

The meeting Doc has two tabs; the Docs API returns only the first unless
`includeTabsContent=True`. If the script doesn't set it, the Raghav+Abdoul tab is
invisible to the whole ops loop.

**AC:** a pull demonstrably contains second-tab content, or the fix is applied.

### PXA-017 — Merge the compendium branch
**P1 · XS · Owner: Claude · Status: done (2026-08-10)**

`claude/pixelagent-research-compendium-9aaa86` (compendium + review + backlog +
approved `AGENTS.md` pointer) is local-only. Push and merge into
`feat/continuing-failure-analysis` so Hermes sessions actually load the pointer.

**AC:** branch pushed; merged; `AGENTS.md` pointer live on the working branch.

### PXA-018 — Stale action-item cleanup
**P2 · XS · Owner: Abdoul · Status: resolved (2026-08-10)**

> ✅ Abdoul ruled **all** June carry-over items dead: SSH key + cron, Babel/Bridges
> guides, 3-paper-ideas assignment, SURA re-application, Skill.md, data-format
> item. They disappear from PROJECT_STATE at the next regen (PXA-015).

Confirmed stale: "[ ] Sign off Phase 0" (manifest shows [x] 2026-07-10);
"evaluation script should emit why a trace failed" (done via eval-bundle
vendoring); "consolidate viewers" (done). Unclear — need a live/dead call each:

- Babel quick-start guide write-up
- Document + share lab-standard Bridges setup with the team
- SSH key for Babel/Bridges usable by Hermes
- Cron jobs to monitor experiments
- `Skill.md` for ramping up on new ideas (Google Workspace CLI instructions)
- 3 paper ideas each (Abdoul / Raghav / Amaad)
- SURA re-application
- "Agree on a common data format for sharing trajectories" (likely superseded by
  packet + `annotations.json`)

**AC:** each item marked live (→ becomes a ticket) or dead (struck in
PROJECT_STATE at next regen).

### PXA-019 — Enable Drive API for the ops service account
**P3 · XS · Owner: Abdoul · Status: optional**

GCP project `pixelagent-500520` (number 804624298804) has the Drive API disabled;
the service account reads Docs by ID but cannot enumerate folders. Enabling it
lets ops scripts discover new Drive docs automatically. The interactive Drive
connector already covers agent sessions, so this is convenience only.

---

## Epic E — SURA report

### PXA-020 — Work through the report review checklist
**P1 · M · Owner: Abdoul · Status: open**

> Ruling 2026-08-10: the report is **live — a paper seed**. Items 1.1 (ceiling
> framing), 1.2 (judge-calibration related work + OSWorld-Verified), and 1.3
> (taxonomy appendix) are the ones that shape the paper.

`docs/reviews/sura-report-review-2026-08-10.md` holds 6 substantive items, 5
corrections, 3 strengtheners. Checklist: `docs/reviews/sura-report-review-2026-08-10.md`.

---


### PXA-021 — Hide judge labels during independent annotation
**P0 · S · Owner: Abdoul · Status: open · Blocks: PXA-008**

Ruled 2026-08-10: judge's provisional labels must be **hidden** (or collapsed
behind an explicit click, default-off) in the review UI until the annotator has
saved their own labels for that trace — otherwise the judge anchors human labels
and human–judge agreement stops being independent validation.

Implementation notes: judge modes reach the UI via `packet_manifest.json` →
`review/packet.py` (`judge_modes_ordered`) → `templates/trace_review/*.j2` +
`review.js`. Gate rendering on `annotations[annotator][key]` existing. **Not
implemented in this pass deliberately** — the trace-review UI is mid-refactor in
the `2a0ebb5` WIP; land it with that refactor to avoid churn.

**AC:** annotator loading an unlabeled trace sees no judge modes; after saving,
judge modes become visible for comparison; dry run (PXA-008) verifies both states.

### PXA-022 — Benchmark-novelty research (from meeting TODO)
**P1 · M (mostly agent time) · Owner: Abdoul · Status: ready — prompt prepared**

The standing meeting TODO: read the space of benchmarks beyond OSWorld and
determine whether existing error analysis there renders our reference-conditioned
judge non-novel. Partially covered by the 2026-07-03 OSWorld-Human literature
report (OSWorld-Human citation graph + judge benchmarks); the uncovered half is
error analyses on *other* benchmarks (WebArena, TheAgentCompany, AndroidWorld,
Mind2Web family, GAIA, OSWorld v2 frontier-lab breakdowns, …).

**A paste-ready deep-research prompt is prepared:**
[`prompts/PXA-022-benchmark-novelty-research.md`](prompts/PXA-022-benchmark-novelty-research.md)
— self-contained, encodes what the July report already established, names the
benchmark list, and specifies the deliverable (table + verdict + borrow list).

**AC:** verdict paragraph exists (novelty intact / threatened / dead, with the
precise remaining delta); table filed in the compendium (05-literature); result
feeds the SURA-paper related-work rewrite (PXA-020 item 1.2).

### PXA-023 — Weekly report undercounts off-branch work
**P2 · S · Owner: Abdoul (or Claude) · Status: open**

`ops/weekly_report.py` counts commits on the checked-out branch only. W28/W29
reported zero commits and zero runs during the busiest stretch of the project
(the work was on `feat/continuing-failure-analysis`). Fix: aggregate across
branches (`git log --all --remotes` with dedup, or per-branch sections), and
state in the report header which refs were scanned.

**AC:** a week with work only on a feature branch produces a non-empty report;
report names the refs it covered.

## Deferred — explicitly not now

| Item | Why deferred |
|---|---|
| Taxonomy 3-category / 19-leaf resolution | Needs PXA-010's discovery-label evidence first; leaf changes deferred unless Abdoul requests |
| Scaled rejudge + prevalence CIs (361 episodes) | Phase D; needs calibrated judge |
| Controlled tracks (zoom / ambiguity / infeasible / relational / cross-app) | Post-gold |
| VTS / Memory Inception stretch goal | Conditional on core pipeline health |
| Throughput scaling of labeling | Meaningful only after the pilot round proves the instrument |
| Amaad's dataset-differentiation track | Research direction, not a blocking action |
