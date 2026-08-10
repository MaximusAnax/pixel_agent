# Handoff — Raghav's open tickets (2026-08-10)

Paste-ready message below; tickets live in `docs/tickets/BACKLOG.md` on
`feat/continuing-failure-analysis`.

---

Hey Raghav — we turned everything outstanding into a ticket backlog
(`docs/tickets/BACKLOG.md` on `feat/continuing-failure-analysis`, just pushed).
Four are yours, one is the critical path:

**PXA-005 — Human Agent screenshots for the 30 pilot tasks** *(P0 — everything
downstream is gated on this)*. The `osworld_v1` rejudge can't run until
`oracle_status` is `ready` or `partial` per task. Artifacts go under the mattlab
shared tree (`human_traj.json` + per-step obs PNGs + `grounding_cache.jsonl`).
Any tasks that end up `failed` — please note *why*; that feeds PXA-011.

**PXA-011 — OSWorld VM init failures**: why is Chrome not open on setup, which
tasks hang, and can we auto-flag or exclude contaminated episodes?

**PXA-012 — Instruction repair for OSWorld-Human**: a method for turning human
trajectories into complete instructions (the missing press-Enter class), with a
before/after human-agent success check on ~10 tasks.

**PXA-014 — Small one**: which model family were the ScreenSpot V2 / OSWorld-G
reproduction rows (7B/32B)? It's not written down anywhere and we need it before
those numbers go in a paper.

**Policy change that affects your labeling:** we ratified **all-applicable**
labels — select *every* mode the evidence supports, ordered
**most-central-first** (position 0 is exported as your "primary," so order
deliberately, not in click order). Instructions are in
`errorAnalysis/docs/trace_review_labeling.md` under "Labeling policy
(ratified 2026-08-10)". The judge, prompt, schema, and agreement metrics have
all been migrated to match, and judge labels will be hidden during independent
labeling to avoid anchoring.

— Abdoul
