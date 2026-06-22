# Automating project-state context

Goal: replace the lossy, manual weekly cadence (someone hand-typing Google Meet
notes; everyone verbally re-syncing) with a **seamless, mostly-automated flow of
information** that keeps both the team and the Hermes multi-agent orchestration
current on the state of the research — and to do it in a way that compounds
toward an eventual Karpathy-style "autoresearch" loop.

This document explains the design, how to set it up, and the roadmap. The code
lives in [`../ops/`](../ops/README.md); Hermes drives it via the
[`project-state-sync`](../hermes/skills/project-state-sync/SKILL.md) skill.

## Problem

Every week a lot of information moves through the project:

- code: PRs merged, refactors, new scripts;
- experiments: Babel runs, new `summary.md`/label artifacts;
- discussion: decisions, feedback, ideas, and action items from the meeting.

Today that is captured by hand (a meeting-notes doc) and re-explained verbally.
Things get missed, and none of it is automatically available to Hermes, which
starts each session from a static `AGENTS.md` with no memory of last week.

## Design

Three stages feeding one canonical state, which Hermes auto-ingests:

```text
                 ┌───────────────────────── INGEST ─────────────────────────┐
 GitHub PRs ────▶│ weekly_report.py  → ops/reports/<ISO-week>.md (+ issue)   │
 commits/diffs ─▶│                                                           │
 experiment runs│                                                           │
                 │ transcribe_meeting.py (local Whisper)                     │
 meeting audio ─▶│   → ops/meetings/<date>/transcript.md                     │
                 │   → ops/meetings/<date>/notes.md   (structured, human/agent)│
                 └───────────────────────────────────────────────────────────┘
                                          │
                 ┌──────────────────── SYNTHESIZE ──────────────────────────┐
                 │ synthesize_state.py (LLM or extractive)                   │
                 │   reads: latest report + recent notes/transcripts + prev  │
                 │   writes: ops/state/PROJECT_STATE.md  (full)              │
                 │           AGENTS.md  Live-project-state block (compact)   │
                 └───────────────────────────────────────────────────────────┘
                                          │
                 ┌──────────────────── CONSUME ─────────────────────────────┐
                 │ Hermes auto-loads AGENTS.md every turn → "just knows" the │
                 │ current focus, decisions, feedback, and open questions.   │
                 └───────────────────────────────────────────────────────────┘
```

### Why these choices

| Decision | Choice | Rationale |
|---|---|---|
| Where jobs run | **GitHub Actions** (weekly cron) | No always-on machine needed; native PR/commit access via `GITHUB_TOKEN`. |
| Transcription | **Local Whisper** (`faster-whisper`) | Audio never leaves the machine; no per-minute cost; CPU-friendly. |
| State store | **In-repo file Hermes auto-loads** | Versioned, diffable, zero extra infra. The managed `AGENTS.md` block is what guarantees Hermes ingests it (it auto-injects `AGENTS.md` every turn — see `hermes_setup.md`). |
| Synthesis | **LLM optional, extractive fallback** | Works with no API key; upgrades to dedup/rewrite quality when a key is present. |

### How Hermes actually ingests it

Per [`hermes_setup.md`](hermes_setup.md), Hermes auto-loads `AGENTS.md` (and
subdir `AGENTS.md`s) every turn, but does **not** auto-read arbitrary files by
name. So the synthesizer writes a compact digest into a **managed block** in
`AGENTS.md`:

```text
<!-- BEGIN:PROJECT_STATE (... do not edit by hand) -->
## Live project state
... compact digest ...
<!-- END:PROJECT_STATE -->
```

The full detail stays in `ops/state/PROJECT_STATE.md` for humans and for Hermes
to open on demand. The block is regenerated each run (idempotent), so never edit
it by hand.

## Setup

### 1. Weekly report in CI (one-time)

`.github/workflows/weekly-report.yml` already runs `weekly_report.py` on a weekly
cron, opens a discussion issue, and commits the report. To change timing, edit
the `cron:` (UTC) to land a few hours before your meeting. No secrets needed
beyond the default `GITHUB_TOKEN`.

You can also run it on demand from the Actions tab (workflow_dispatch).

### 2. Transcription (local, per meeting)

```bash
cd errorAnalysis
pip install -r ops/requirements.txt   # faster-whisper; also `brew install ffmpeg`
python ops/transcribe_meeting.py path/to/recording.m4a --date YYYY-MM-DD
```

Record the meeting however you like (QuickTime, Meet local recording, phone).
Point the script at the file; it writes `ops/meetings/<date>/transcript.md` and
seeds `notes.md`.

### 3. Notes (structured, high-signal)

Fill `ops/meetings/<date>/notes.md` during/after the meeting using the template
headings: **Decisions made**, **Feedback / critiques**, **Ideas considered**,
**Action items**, **Open questions**. These flow into the state with provenance.
(This can itself be agent-assisted: ask Hermes to draft `notes.md` from the
transcript, then a human corrects it.)

### 4. Synthesis

```bash
python ops/synthesize_state.py --meetings 3        # extractive by default
# with an LLM:
export OPENAI_API_KEY=...        # or STATE_LLM_API_KEY (+ STATE_LLM_BASE_URL/MODEL)
python ops/synthesize_state.py --meetings 3
```

Commit `ops/reports`, `ops/meetings`, `ops/state`, and `AGENTS.md`. Raw audio is
git-ignored.

### 5. (Optional) Fully hands-off

Have Hermes own the loop via the `project-state-sync` skill on its VPS: a cron
that (a) runs the report pre-meeting, (b) after you drop a recording, transcribes
+ drafts notes + synthesizes, and (c) commits. Humans only correct `notes.md`.

## Roadmap toward autoresearch

This is stage 1 (sense + remember). The natural progression:

1. **Now — shared memory.** Auto report + transcribed meetings + synthesized
   state that Hermes always sees. *(this change)*
2. **Action extraction.** Turn `Action items` into tracked GitHub issues
   automatically; close the loop by reporting their status in the next report.
3. **Decision-aware planning.** Hermes proposes next experiments from
   `PROJECT_STATE.md` (open questions + recent results) for human approval.
4. **Closed experiment loop.** Approved proposals become Babel runs via the
   existing `babel-osworld-analysis` skill; results feed the next report
   automatically.
5. **Autoresearch.** The loop runs with humans mostly approving/steering rather
   than driving — Karpathy-style — built on the same memory substrate.

Each step is additive and keeps a human in the loop until explicitly relaxed,
consistent with the project's Phase-1 scientific posture (evidence over
confident guesses).

## Privacy & boundaries

- Raw recordings stay local (git-ignored); only text artifacts are committed.
- Transcripts are evidence, not ground truth — structured `notes.md` is higher
  signal.
- The synthesizer never invents decisions; with no LLM it is purely extractive.
- The `AGENTS.md` Phase-1 boundaries (no raw-trajectory downloads, no taxonomy
  edits without Andi, etc.) are unaffected — the state block is additive.
