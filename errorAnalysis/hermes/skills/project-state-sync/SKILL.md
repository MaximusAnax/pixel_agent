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
      - key: babel.project_dir
        description: Local path to the errorAnalysis project root (where ops/* live)
        default: "~/Documents/School/Research/pixelAgent/errorAnalysis"
        prompt: "Local errorAnalysis project directory"
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
meeting recording ──▶ ops/transcribe_meeting.py ─▶ ops/meetings/<date>/transcript.md
                                                    ops/meetings/<date>/notes.md (human/agent)
                                                              │
   report + notes + transcript + prev state ─▶ ops/synthesize_state.py
                                                              │
                          ops/state/PROJECT_STATE.md  +  AGENTS.md  (Live project state block)
                                                              │
                                                              ▼
                                              Hermes auto-loads it every turn
```

## Procedure

All commands run from the project directory (`babel.project_dir`).

### 1. Generate the weekly report (pre-meeting)

```bash
python ops/weekly_report.py --days 7            # writes ops/reports/<week>.md
# or, to also file a GitHub issue for discussion:
python ops/weekly_report.py --days 7 --open-issue
```

Read the result and report to Andi using the project Output Standard (model/
package, episodes, labels, adapter gaps where relevant). The `## To discuss` and
`## Next week's targets` sections are for humans — leave them for the team.

### 2. After a meeting: transcribe (local, audio stays on the machine)

```bash
python ops/transcribe_meeting.py path/to/recording.m4a --date YYYY-MM-DD
```

This creates `ops/meetings/<date>/transcript.md` and seeds `notes.md` from the
template. Encourage Andi (or do it yourself if asked) to fill the structured
headings in `notes.md` — Decisions, Feedback, Ideas, Action items, Open
questions — since those flow verbatim into the state.

### 3. Synthesize the living state

```bash
python ops/synthesize_state.py --meetings 3
```

- If an OpenAI-compatible endpoint is configured (`STATE_LLM_API_KEY` or
  `OPENAI_API_KEY`, plus optional `STATE_LLM_BASE_URL` / `STATE_LLM_MODEL`), this
  deduplicates and rewrites the state with an LLM.
- Otherwise it runs a deterministic extractive merge (no key needed).

It rewrites `ops/state/PROJECT_STATE.md` and the managed block in `AGENTS.md`
(between the `BEGIN:PROJECT_STATE` / `END:PROJECT_STATE` markers). Never edit that
block by hand — it is regenerated.

Use `--dry-run` to preview, `--no-llm` to force extractive mode.

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
- `synthesize_state.py` reads only the last `--meetings N` meetings (default 3).
  Bump it if you need to re-fold older context.
- Transcripts can be noisy; treat them as evidence, not ground truth. Structured
  `notes.md` is the higher-signal input.
- Do not commit raw audio (it is git-ignored and may be sensitive).

## Verification

- `ops/reports/<ISO-week>.md` exists and shows non-empty "At a glance" counts.
- `ops/state/PROJECT_STATE.md` exists and its "As of" date is today.
- `AGENTS.md` contains exactly one `BEGIN:PROJECT_STATE` / `END:PROJECT_STATE`
  pair, with the latest digest between them.
