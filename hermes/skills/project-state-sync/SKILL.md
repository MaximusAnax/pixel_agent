---
name: project-state-sync
description: Keep Hermes' project context current by generating the weekly progress report and synthesizing meeting notes + reports into PROJECT_STATE.md and the AGENTS.md live-state block. Use before weekly meetings, after a meeting is transcribed, or whenever Andi asks "what's the current state?".
version: 1.0.0
author: pixelAgent / CUA Failure Analysis
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Research, ProjectOps, Reporting, Context]
    requires_toolsets: [terminal, file]
    config:
      - key: project.root
        description: Local path to the pixelAgent git root (where ops/* and AGENTS.md live)
        default: "~/Documents/School/Research/pixelAgent"
        prompt: "pixelAgent repository root"
---

# Project State Sync

Maintain the closed-loop information flow so the orchestration always knows the
latest state of the research project: merged PRs, code changes, experiment runs,
and what was decided/discussed in the weekly meeting.

## When to Use

- **Before the weekly meeting:** produce the draft progress report.
- **After a meeting is recorded/transcribed:** fold the notes into the living state.
- **Any time Andi asks "what's our current state?"** read `ops/state/PROJECT_STATE.md`
  (and remember the `Live project state` block in `AGENTS.md` is already in your
  context every turn).

Do NOT invent decisions or progress. Only synthesize from the actual report and
meeting artifacts. Flag anything uncertain as provisional.

## The information flow

```text
GitHub PRs/commits ─┐
experiment outputs ─┼─▶ ops/weekly_report.py ─▶ ops/reports/<ISO-week>.md
                    │
Google Doc notes ───▶ ops/pull_gdoc_notes.py ─▶ ops/meetings/<date>/gdoc_notes.md (PRIMARY)
Wispr supplement ───▶ ops/pull_wispr_context.py (optional)
Zoom recording ─────▶ ops/transcribe_meeting.py (optional fallback)
                                                              │
   report + gdoc + supplements + prev state ─▶ ops/synthesize_state.py
                                                              │
                          ops/state/PROJECT_STATE.md  +  AGENTS.md  (Live project state block)
                                                              │
                                                              ▼
                                              Hermes auto-loads it every turn
```

## Procedure

All commands run from the **pixelAgent repo root** (`project.root` config value).

### 1. Generate the weekly report (pre-meeting)

```bash
python ops/weekly_report.py --days 7            # LLM narrative if key set
python ops/weekly_report.py --days 7 --no-llm   # extractive narrative
# or, to also file a GitHub issue for discussion:
python ops/weekly_report.py --days 7 --open-issue
```

The report leads with **Executive summary**, **Key advancements**, and **Experiment
findings** (deduped runs); raw PR/run lists live in a collapsed appendix.

Read the result and report to Andi using the project Output Standard (model/
package, episodes, labels, adapter gaps where relevant). The `## To discuss` and
`## Next week's targets` sections are for humans — leave them for the team.

### 2. After a meeting: pull and format Google Doc notes (primary)

```bash
python ops/pull_gdoc_notes.py --date YYYY-MM-DD --section-only   # rolling doc
python ops/format_meeting_notes.py --date YYYY-MM-DD             # Anthropic → notes.md
python ops/pull_wispr_context.py --date YYYY-MM-DD               # optional Wispr supplement
```

Requires `ANTHROPIC_API_KEY` in env or `ops/config/meetings.env` for formatting.
Setup: service account + share the Doc — see `docs/meeting_notes_workflow.md`.

Optional: `transcribe_meeting.py` only if you need a Zoom recording transcript fallback.

### 3. Synthesize the living state

```bash
python ops/synthesize_state.py
```

- Default **`--meetings 1`**: only the latest meeting folder is new input; LLM mode
  merges into the previous `PROJECT_STATE.md` (add relevant, update/drop stale).
- If `ANTHROPIC_API_KEY` is configured (or in `ops/config/meetings.env`), this
  auto-formats raw `gdoc_notes.md` → `notes.md` then synthesizes with Claude.
  OpenAI is available via `STATE_LLM_PROVIDER=openai`.
- Otherwise it runs a deterministic extractive merge (no key needed; weaker cumulative
  memory — prefer LLM mode for incremental updates).
- Use `--meetings N` to re-read several recent folders in one pass (e.g. after a
  missed week).

It rewrites `ops/state/PROJECT_STATE.md` and the managed block in `AGENTS.md`
(between the `BEGIN:PROJECT_STATE` / `END:PROJECT_STATE` markers). Never edit that
block by hand — it is regenerated.

Use `--dry-run` to preview, `--no-llm` to force extractive mode.

Optional: run locally the same steps as CI (see `.github/workflows/post-meeting-sync.yml`).

### 4. Commit the updated context

```bash
git add ops/reports ops/meetings ops/state AGENTS.md
git commit -m "chore(ops): sync project state $(date +%F)"
```

(Raw recordings are git-ignored; only transcripts/notes/state are committed.)

## Pitfalls

- The `AGENTS.md` live-state block is generated. If you edit it manually it will
  be overwritten on the next `synthesize_state.py` run — put durable instructions
  elsewhere in `AGENTS.md`.
- `synthesize_state.py` reads only the last `--meetings N` meetings (default **1**).
  LLM mode merges that input into the previous `PROJECT_STATE.md`; bump N only when
  re-folding several missed weeks.
- Transcripts can be noisy; treat them as evidence, not ground truth. Structured
  `notes.md` is the higher-signal input.
- Do not commit raw audio (it is git-ignored and may be sensitive).

## Verification

- `ops/reports/<ISO-week>.md` exists with **Executive summary** (or legacy **At a glance**).
- `ops/state/PROJECT_STATE.md` exists and its "As of" date is today.
- `AGENTS.md` contains exactly one `BEGIN:PROJECT_STATE` / `END:PROJECT_STATE`
  pair, with the latest digest between them.
