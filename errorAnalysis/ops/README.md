# ops/ — Automated project-state context

A closed loop that keeps everyone (humans **and** the Hermes orchestration) in
sync on the state of the research project, with as little manual work as possible.

It does three things:

1. **Drafts a weekly progress report** before the meeting — merged PRs, code
   churn, and new experiment runs — so the team starts from a draft, not a blank
   page.
2. **Transcribes each meeting** locally (audio never leaves the machine) and
   stores transcript + structured notes in-repo.
3. **Synthesizes** the report + meeting notes into a living `PROJECT_STATE.md`
   and a compact block inside `../AGENTS.md`, which Hermes auto-loads every turn.
   The orchestration therefore "just knows" the latest decisions, feedback, and
   open questions.

This is the first concrete step toward a seamless information flow for the
multi-agent system — the substrate an eventual Karpathy-style "autoresearch"
loop would build on.

## The loop

```text
GitHub PRs/commits ─┐
experiment outputs ─┼─▶ weekly_report.py ─▶ reports/<ISO-week>.md ──┐
                    │                          (+ GitHub issue)      │
meeting recording ──▶ transcribe_meeting.py ─▶ meetings/<date>/ ─────┤
                          (Whisper, local)      transcript.md        │
                                                notes.md (filled in) │
                                                                     ▼
                       prev state + report + notes ─▶ synthesize_state.py
                                                                     │
                          state/PROJECT_STATE.md   +   ../AGENTS.md block
                                                                     │
                                                                     ▼
                                              Hermes auto-loads it every turn
```

## Components

| Path | What it is |
|---|---|
| `weekly_report.py` | Stdlib + `git`/`gh`. Builds `reports/<ISO-week>.md`. Runs in GitHub Actions. |
| `transcribe_meeting.py` | Local Whisper (`faster-whisper`) → `meetings/<date>/transcript.md`. |
| `synthesize_state.py` | Merges report + meeting notes → `state/PROJECT_STATE.md` + `AGENTS.md` block. Optional LLM. |
| `meetings/_TEMPLATE_notes.md` | The structured-notes template (Decisions, Feedback, Ideas, Action items, Open questions). |
| `reports/`, `meetings/`, `state/` | Generated artifacts (committed). Raw audio is git-ignored. |
| `../hermes/skills/project-state-sync/` | Hermes skill that drives this whole loop. |
| `../../.github/workflows/weekly-report.yml` | Weekly cron that runs the report and opens an issue. |

## Quick start

```bash
# from errorAnalysis/
pip install -r ops/requirements.txt           # only needed for transcription

# 1. Pre-meeting report (also runs weekly in CI)
python ops/weekly_report.py --days 7           # --open-issue to file a GH issue

# 2. After the meeting, transcribe the recording
python ops/transcribe_meeting.py ~/Downloads/standup-2026-06-22.m4a

# 3. Fill in meetings/<date>/notes.md (Decisions / Ideas / Action items / …)

# 4. Synthesize the living state Hermes reads
python ops/synthesize_state.py --meetings 3    # --dry-run to preview

# 5. Commit transcripts/notes/state (audio is git-ignored)
git add ops/reports ops/meetings ops/state AGENTS.md && git commit -m "chore(ops): sync state"
```

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `GH_TOKEN` / `gh auth` | `weekly_report.py` | List merged PRs, open issues. Auto-set in Actions. |
| `STATE_LLM_API_KEY` or `OPENAI_API_KEY` | `synthesize_state.py` | Enable LLM synthesis (else extractive). |
| `STATE_LLM_BASE_URL` | `synthesize_state.py` | OpenAI-compatible endpoint (default `https://api.openai.com/v1`). |
| `STATE_LLM_MODEL` | `synthesize_state.py` | Model id (default `gpt-4o-mini`). |

LLM synthesis is optional. Without a key, `synthesize_state.py` runs a
deterministic extractive merge that is still useful — the difference is
deduplication/rewriting quality.

## Design choices (and how to change them)

- **Runner: GitHub Actions.** No machine to keep on; native PR/commit access.
  To move to the Hermes VPS instead, drop the workflow and have the
  `project-state-sync` skill run `weekly_report.py` on a `cronjob`.
- **Transcription: local Whisper.** Privacy-preserving; no per-minute cost. Swap
  the `transcribe()` body in `transcribe_meeting.py` for another backend if you
  later use Google Meet/Otter exports — the rest of the loop is unchanged.
- **State store: in-repo file Hermes auto-loads.** Versioned and diffable. The
  canonical detail is `state/PROJECT_STATE.md`; the always-injected digest is the
  managed block in `AGENTS.md`. If you also want a human-facing Google Doc, add a
  one-way mirror step from `PROJECT_STATE.md`.

See `../docs/project_state_automation.md` for the full rationale, setup, and
roadmap toward autoresearch.
