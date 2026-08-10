# ops/ — Cross-stage project operations (repo root)

Automation that applies to **every** pixelAgent stage: weekly progress reports,
meeting notes ingest (Google Docs + optional Wispr), and synthesis into
`PROJECT_STATE.md` plus the managed block in the **repo-root** `AGENTS.md`.

Run all commands from the **pixelAgent/** git root (not from `errorAnalysis/`).

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
| `weekly_report.py` | Stdlib + `git`/`gh` + optional Anthropic narrative. Builds `reports/<ISO-week>.md`. Runs in GitHub Actions. |
| `pull_gdoc_notes.py` | Google Docs API → `meetings/<date>/gdoc_notes.md` (raw pull). |
| `format_meeting_notes.py` | Anthropic → structured `meetings/<date>/notes.md`. |
| `llm_client.py` | Shared Anthropic (default) / OpenAI LLM client. |
| `pull_wispr_context.py` | Local Wispr Flow SQLite → optional `wispr_supplement.md`. |
| `transcribe_meeting.py` | Optional Whisper fallback for Zoom recordings. |
| `synthesize_state.py` | Merges report + meeting notes → `state/PROJECT_STATE.md` + `AGENTS.md` block. Optional LLM. |
| `meetings/_TEMPLATE_notes.md` | The structured-notes template (Decisions, Feedback, Ideas, Action items, Open questions). |
| `reports/`, `meetings/`, `state/` | Generated artifacts (committed). Raw audio is git-ignored. |
| `../hermes/skills/project-state-sync/` | Hermes skill (repo root, cross-stage). |
| `../../.github/workflows/weekly-report.yml` | Weekly cron (pre-meeting report). |
| `../../.github/workflows/post-meeting-sync.yml` | Weekly cron (post-meeting gdoc pull + synthesize). |

## Quick start

```bash
# from pixelAgent/ (repo root)
pip install -r ops/requirements.txt

# 1. Pre-meeting report (also runs weekly in CI)
python ops/weekly_report.py --days 7           # LLM narrative if ANTHROPIC_API_KEY set
python ops/weekly_report.py --days 7 --no-llm  # extractive narrative only

# 2. After the meeting — pull shared Google Doc notes
python ops/pull_gdoc_notes.py --date 2026-06-27 --section-only
python ops/format_meeting_notes.py --date 2026-06-27   # Anthropic → notes.md
python ops/pull_wispr_context.py --date 2026-06-27   # optional (Mac + Wispr)

# 3. Synthesize the living state Hermes reads (auto-formats if notes.md missing)
python ops/synthesize_state.py    # default: last 1 meeting → merge into prev state

# 5. Commit transcripts/notes/state (audio is git-ignored)
git add ops/reports ops/meetings ops/state AGENTS.md && git commit -m "chore(ops): sync state"
```

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `GH_TOKEN` / `gh auth` | `weekly_report.py` | List merged PRs, open issues. Auto-set in Actions. |
| `ANTHROPIC_API_KEY` | LLM scripts | Formatting + weekly report narrative + synthesis. Default model `claude-sonnet-4-6`. |
| `STATE_LLM_MODEL` | LLM scripts | Optional override only. |
| `STATE_LLM_PROVIDER` | `llm_client.py` | Force `anthropic` or `openai` (optional). |
| `OPENAI_API_KEY` | LLM scripts | Only if `STATE_LLM_PROVIDER=openai`. |
| `STATE_LLM_BASE_URL` | OpenAI provider | OpenAI-compatible endpoint. |

LLM steps are optional. Without `ANTHROPIC_API_KEY`, `weekly_report.py` and
`synthesize_state.py` use extractive mode; `format_meeting_notes.py` will exit with an error.

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

See `docs/meeting_notes_workflow.md` and `docs/project_state_automation.md`.
When adding a second idea stage or multi-idea Hermes orchestration, read
`docs/multi_idea_stages.md`.
