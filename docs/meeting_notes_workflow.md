# Meeting notes workflow (Zoom + Google Docs + Wispr Flow)

This replaces the original design (local Whisper + hand-filled `notes.md`) with
your **actual** weekly cadence: Zoom call, notes in a **shared Google Doc**, often
dictated via **Wispr Flow**.

## Reworked loop

```text
┌─ PRE-MEETING ──────────────────────────────────────────────────────────┐
│  weekly_report.py (GitHub Actions, Fridays) → ops/reports/<week>.md   │
└────────────────────────────────────────────────────────────────────────┘
                                    │
┌─ DURING MEETING (unchanged for humans) ────────────────────────────────┐
│  Zoom video call                                                       │
│  Notes in shared Google Doc (typed +/or Wispr dictation into the Doc)  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
┌─ AFTER MEETING (automated pull) ───────────────────────────────────────┐
│  pull_gdoc_notes.py  → meetings/<date>/gdoc_notes.md   (PRIMARY)       │
│  pull_wispr_context.py → meetings/<date>/wispr_supplement.md (optional)│
│  notes.md              → optional structured overlay                   │
│  transcript.md         → optional Zoom/local fallback                  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                       synthesize_state.py → PROJECT_STATE.md + AGENTS.md
                       (default: last 1 meeting merged into previous state)
                                    │
                              Hermes auto-loads every turn
```

**Source-of-truth priority:** Google Doc → structured `notes.md` overlay → Wispr
supplement → transcript.

---

## Wispr Flow — deep dive (what helps your workflow)

Wispr Flow is **not** a meeting recorder like Otter or Zoom AI. It is a
**system-wide voice-to-text layer**: you hold a hotkey, speak, and polished text
is inserted wherever your cursor is — including **Google Docs**, Slack, Cursor,
etc.

Official docs: [docs.wisprflow.ai](https://docs.wisprflow.ai) · Developer API:
[api-docs.wisprflow.ai](https://api-docs.wisprflow.ai/introduction)

### What Wispr is good at for *your* setup

| Capability | How it helps |
|---|---|
| **Dictate into Google Docs** | You keep one shared Doc; Wispr cleans filler words and formats paragraphs while you talk. **This is already the best integration** — no export pipeline needed for Doc content. |
| **Context-aware formatting** | Detects app (Docs vs Slack vs Cursor) and adjusts tone/structure ([product guide](https://docs.wisprflow.ai)). |
| **Custom dictionary / snippets** | Names (OpenCUA, Babel, OSWorld), repo paths, model names — fewer transcription errors in research notes. |
| **Scratchpad / Notes** | Floating notes synced across Mac/iOS ([Scratchpad docs](https://docs.wisprflow.ai/articles/9618237082-using-the-scratchpad-to-save-and-edit-notes)). Side thoughts during the meeting — **not** auto-linked to Google Docs; use `pull_wispr_context.py` or copy-paste. |
| **Cross-device sync** | Same account on Mac + phone; dictation history when Cloud Sync is on. |

### What Wispr does **not** provide (important)

| Gap | Implication |
|---|---|
| **No native Google Docs sync/export** | Wispr does not push Scratchpad or history into your Doc. The **Google Doc pull** (`pull_gdoc_notes.py`) remains the automation entry point. |
| **No public webhook for “meeting ended”** | Developer API is **speech-to-text** (REST/WebSocket), not event-driven meeting ingestion. |
| **Voice API ≠ full meeting transcription** | REST chunks are **≤6 minutes / 25MB** per request — fine for dictation clips, not a 60-minute Zoom recording. |
| **No individual bulk history API** | Enterprise GDPR export via account rep; Admin Portal CSV is **usage metrics**, not full transcript text ([security FAQ](https://docs.wisprflow.ai/articles/3467817258-security-and-compliance-faq)). |
| **Dictation history export** | Only when **Cloud Sync** stores data on Wispr servers; ZDR/off = not exportable from cloud. |

### Wispr tools that *can* feed the agent loop

| Tool | Type | Use in pixelAgent |
|---|---|---|
| **Dictate into Google Doc** | Built-in | Primary human workflow; captured by `pull_gdoc_notes.py`. |
| **Local SQLite history** | Desktop (`~/Library/Application Support/Wispr Flow/flow.sqlite`) | `pull_wispr_context.py` — dictations during meeting window, optional app filter. Same DB as [WisprMCP](https://github.com/pedramamini/WisprMCP). |
| **Scratchpad** | Built-in | Manual copy into Doc or weekly section; or pull via Wispr DB if dictated there. |
| **Voice Interface API** | Developer ([api-docs.wisprflow.ai](https://api-docs.wisprflow.ai)) | Future: custom “structure this Doc section” micro-service; overkill for v1. |
| **Admin Portal export** | Enterprise CSV | Team adoption metrics only — not meeting content. |

### Recommended Wispr setup for research meetings

1. **Enable Context Awareness** (Settings → Data and Privacy) so Docs get structured paragraphs.
2. **Build a custom dictionary**: OpenCUA, OSWorld, Babel, Slurm, Hermes, Kimi, etc.
3. **Dictate directly into the shared Google Doc** during Zoom — don't rely on Scratchpad for main notes.
4. **Optional:** After the meeting, run `pull_wispr_context.py` to capture dictations into Cursor/Slack during the call window.
5. **Optional LLM formatting + synthesis** — set `ANTHROPIC_API_KEY` in
   `ops/config/meetings.env` (see below). Especially valuable for free-form rolling
   docs like yours.

### Wispr vs other capture options

| Source | Role |
|---|---|
| **Google Doc** | Canonical meeting notes (technologies, ideas, decisions). |
| **Wispr → Doc** | Input method into canonical doc. |
| **Wispr local DB** | Supplementary side dictations. |
| **Zoom cloud transcript** | Optional verbatim backup (VTT via Zoom API if cloud recording + transcription enabled). Future: `pull_zoom_transcript.py`. |
| **Local Whisper** | Fallback if you download Zoom recording; `transcribe_meeting.py` (optional dep). |

---

## Google Docs pull — setup

### 1. GCP + service account (one-time)

1. [Google Cloud Console](https://console.cloud.google.com/) → create/select project.
2. Enable **Google Docs API**.
3. **IAM → Service Accounts** → create → download JSON key.
4. Save key as `ops/config/gdoc-service-account.json` (git-ignored).
5. Copy the service account email (`...@....iam.gserviceaccount.com`).
6. Open your **meeting notes Google Doc** → Share → add that email as **Viewer**.

### 2. Project config

```bash
cd ~/Documents/School/Research/pixelAgent   # repo root
cp ops/config/meetings.env.example ops/config/meetings.env
pip install -r ops/requirements.txt
```

Edit `ops/config/meetings.env`:

```bash
MEETING_GDOC_ID=https://docs.google.com/document/d/YOUR_DOC_ID/edit
GOOGLE_SERVICE_ACCOUNT_FILE=ops/config/gdoc-service-account.json
MEETING_START=11:00
MEETING_END=12:30

# Anthropic — formatting + state synthesis (uses default model claude-sonnet-4-6)
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Pull after each meeting

```bash
# Rolling doc (one Doc with dated sections) — recommended if Calendar attaches the same doc:
python ops/pull_gdoc_notes.py --date 2026-06-27 --section-only

# Or separate doc per week:
python ops/pull_gdoc_notes.py --date 2026-06-27

# Optional Wispr supplement (Mac, Wispr installed):
python ops/pull_wispr_context.py --date 2026-06-27

# Format raw gdoc → structured notes.md (Anthropic; needs ANTHROPIC_API_KEY):
python ops/format_meeting_notes.py --date 2026-06-27

# Synthesize into Hermes context (auto-formats gdoc if notes.md missing):
python ops/synthesize_state.py
```

### 4. Verify outputs

```bash
ls ops/meetings/2026-06-27/
# gdoc_notes.md   notes.md   meta.json   [wispr_supplement.md]

head -40 ops/meetings/2026-06-27/notes.md
python ops/synthesize_state.py --dry-run | head -60
grep -A20 'BEGIN:PROJECT_STATE' AGENTS.md
```

---

## Google Doc structure tips (for better agent context)

The synthesizer parses `## Heading` sections if present. Recommended headings in
your shared Doc (Wispr can dictate them):

```markdown
## 2026-06-27 — Weekly sync

### Technologies discussed
- ...

### Decisions
- ...

### Ideas / research directions for ...

### Action items
- [ ] @andi — ...
```

If the Doc is free-form (or a rolling multi-week doc), run **`format_meeting_notes.py`**
with Anthropic, then **`synthesize_state.py`**. Manual `##` headings in the Doc are
optional but help.

---

## Artifact reference

| File | Source | Committed? |
|---|---|---|
| `gdoc_notes.md` | `pull_gdoc_notes.py` | Yes (raw pull) |
| `notes.md` | `format_meeting_notes.py` (Anthropic) or manual | Yes (structured) |
| `meta.json` | pull scripts | Yes |
| `wispr_supplement.md` | `pull_wispr_context.py` | Yes |
| `gdoc-service-account.json` | GCP | **No** (git-ignored) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `403` / permission denied on Doc pull | Share Doc with service account email |
| `Service account file not found` | Path in `meetings.env`; file under `ops/config/` |
| `--section-only` pulls whole doc | Add a heading containing `YYYY-MM-DD` or `June 27, 2026` |
| Wispr DB not found | Wispr Flow desktop not installed, or non-Mac (path differs) |
| Empty structured sections in state | Run `format_meeting_notes.py` first; set `ANTHROPIC_API_KEY` |
| `format_meeting_notes.py` exits 2 | Add `ANTHROPIC_API_KEY` to `ops/config/meetings.env` |
| Hermes doesn't see new ideas | Run `synthesize_state.py` and commit `AGENTS.md` + `ops/state/` |

See also: [project_state_automation.md](project_state_automation.md), [ops/README.md](../ops/README.md).
