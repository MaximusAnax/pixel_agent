# 9 — Sources

Everything the compendium was built from, with re-pull instructions. Compiled
2026-08-10 against `feat/continuing-failure-analysis` @ `4829e57`.

> **Lesson from the first pass.** The compendium was initially compiled against
> `1635748` on `main` — 17 commits and 205 files behind the live branch. It
> described a phantom `2026-06-26` meeting that had already been deleted upstream,
> missed the entire Phase 0 freeze, and stated a current milestone that had been
> superseded. **Always record and check the base commit.** `main` is not where this
> project's work lives.

## Google Drive

Project folder: [`1MjmtaI0zDhZiR1al56nxX1ROiYX4KxjK`](https://drive.google.com/drive/folders/1MjmtaI0zDhZiR1al56nxX1ROiYX4KxjK)
· owner `andiongu@andrew.cmu.edu`

### Root

| Document | ID | Modified | What it holds |
|---|---|---|---|
| **Pixel Agent Meeting Notes (Abdoul + Raghav + Amaad + Matt)** | `1zA6q0mtIGTWwnIo7IRwK1_zgE0X6QwQVKtVYjueJock` | 2026-08-07 | The primary record. **Two tabs**: `Everyone` (full-team, reverse-chronological, undated sections) and `Raghav + Abdoul` (working sessions). Contains the 60/361 result, grounding reproduction table, all decisions, the idea backlog. |
| **SURA EOS Report** | `1sew7qpLte-IHxFanj4sTAZ94oCwkBDb53wn6j9GnrEM` | 2026-07-31 | Abdoul's end-of-summer narrative. The most candid account of the project's arc and what is genuinely unfinished. Appendix has the 3-category taxonomy. |

### `Failure Mode Analysis/` — `1hGz1OVF4UcG_C-SalAv6N8cj7eouIVw2`

| Document | ID | What it holds |
|---|---|---|
| **Report on OSWorld-Human and Human-Trajectory Benchmarks for Failure-Analysis Judge Calibration** (.docx) | `1XATf90pJ_fdjhNTFccupbc9m_d_j9xhN` | The literature review that establishes novelty. Surveys AgentRewardBench, WebJudge, TRAIL, AgentRx, AgentProcessBench, and the human-trajectory dataset landscape. Proposes the layered judge design. **The most under-used document in the project.** |
| **Taxonomy of CUA Failure Modes** | `1j4O5HHUgIdQws_l6eN25kRD1l47JLpKhrML7DgtTV1c` | Taxonomy **V1** — 14 leaves, 2 categories, no decision rules. |
| **Stress Testing CUAs: Failure Mode Analysis and Evaluation** | `1P_Za-LNvyt--Lez6bWr3rFOni0hgSVsn3jYSN4H9Z48` | Controlled-experiment plan: variable visuals, ambiguity injection, Pass^k, evaluator audit, human-in-the-loop simulation, proposed metrics. Proposes uncovered modes (Context Saturation Latency, Cross-Application Context Loss, Evaluator Bypass). *Open comment from Amaad: "We should update with newest models"; Abdoul reply: "Find frontier open-weight model to compare against."* |
| **Literature-backed failure mitigation strategies** | `1luu6PljOwSO0B_adXuuz6Mu9xhlYLmum69z-wiR3PQI` | Documented behavioral patterns + mitigations: instruction clarification, CALL_USER, iterative plan extraction, RegionFocus, Image-as-Map, JEDI, self-correction loops. |

### `Ideation/` — `1Dwi7gYdfKzt4eO3HEklsm3KDuF0XU4-m`

| Document | ID | What it holds |
|---|---|---|
| **Research Ideation Tracker** | `1WQ8l62fvmsgJnDFcO2nXZ5xyZuU-f5NuaRMwXhGnzsg` | Idea template + Directions A (world models), B (PRM), C (VTS). Baseline/target metrics table. |
| **Visual Trajectory Steering via MI** | `1OER33k6X-mEUQD-M64-_tE1bmAQfQ1lhOdrvsoiH6mg` | Full VTS stretch-goal proposal: keyframes → Image-as-Map markers → heuristic cards → latent KV banks. |

### `Literature/` — `1P8DXpOUxt80EHa3PUQIbPbsZq7PJ91Ka`

| Document | ID | What it holds |
|---|---|---|
| **Reading List** | `1FTZynvG6FDnudFxU7uGDECcUJsK9PsQ_MO8uOd3EuuE` | Canonical link list: benchmarks, models, PRM, error analysis, game AI. Abdoul's "read" comments mark what's been covered. |
| **Implications of memory inception for Efficient LLM Reasoning** | `1vdHnrJJEY1uVhou46y5Cxb5h5vKIt6fyvxbd6poAGrs` | Why MI matters for small models: KV footprint, selective allocation, pre-RoPE position independence, long-context persistence, loop mitigation via updateable guidance. |

### Re-pulling

Two paths, and they have different capabilities:

**Interactive Drive connector** (agent sessions) — can list folders and read files.
Enumerate with `parentId = '<folder_id>'`; read with the file ID.

**Service account** (`ops/pull_gdoc_notes.py`, CI) —
`pixelagent@pixelagent-500520.iam.gserviceaccount.com`, key at
`ops/config/gdoc-service-account.json`. Reads **Docs by ID only**: the Drive API is
currently disabled in GCP project `pixelagent-500520`, so it cannot list folders.
Enable it at the Google Cloud console for project number `804624298804` if you want
folder enumeration from scripts.

```bash
python ops/pull_gdoc_notes.py --date YYYY-MM-DD --section-only
python ops/synthesize_state.py
```

The meeting Doc uses **Google Docs tabs**; the Docs API needs
`includeTabsContent=True` or you only get the first tab. Verify
`pull_gdoc_notes.py` sets it — the `Raghav + Abdoul` tab is otherwise invisible to
the pipeline.

## Local

| Source | Path |
|---|---|
| **SURA Report** (2026-08-03) | `~/Downloads/PixelAgent_Research.pdf` — 6 pages. Formal write-up: abstract, dataset/task, related work, approach, expected outcomes, plan, appendices. Reviewed in this session; findings in [`08-decisions-and-questions.md`](08-decisions-and-questions.md) and [`03-failure-taxonomy.md`](03-failure-taxonomy.md). |

## Repo

`github.com/MaximusAnax/pixel_agent`

**Active branch: `feat/continuing-failure-analysis`.** `main` is stale.

- Root `AGENTS.md` — project brain, boundaries, freeze pointer, auto-generated
  `PROJECT_STATE` block. **Frozen doc.**
- `errorAnalysis/docs/GROUNDING_MANIFEST.md` — the freeze policy and file inventory.
  Read this before editing anything under `errorAnalysis/`.
- `errorAnalysis/` frozen: `failureAnalysisFinalPlan.md` (v1.1),
  `failureStudyProtocol.md`, `failureTaxonomy.md`, `failureAnalysisPlan.md`,
  `AGENTS.md`, `hermes/SOUL.md`
- `errorAnalysis/docs/` operational (not frozen): `oracle_agent.md`,
  `trace_review_labeling.md`, `babel_hf_orchestration.md`, `vllm_runbook.md`,
  `babel_account_checklist.md`, `osworld_vm_strategy.md`, `mockups/`
- `ops/` — `state/PROJECT_STATE.md` (as of 2026-07-10), `meetings/2026-06-24`,
  `meetings/2026-07-10`, `meetings/2026-08-07`, `reports/2026-W26.md`, `weekly_report_lib.py`
- `docs/` — `meeting_notes_workflow.md`, `project_state_automation.md`,
  `multi_idea_stages.md`, `compendium/`, `reviews/`

## Gaps in this compendium

Be honest about what was not available:

- **No meeting in this project is reliably dated.** The Doc has **no dated
  sections** — every section header carries a blank "Attendees:" line. The
  `2026-06-24` and `2026-06-26` folders in `ops/meetings/` are named for when
  `pull_gdoc_notes.py` was run, and each contains a dump of the *whole* Doc rather
  than one meeting's section. So statements are cited as "late June," "a later
  meeting," or "the most recent meeting," and the number of meetings held is
  unknown. Fixing this upstream (dating each Doc section, then re-pulling) would
  retroactively repair the meeting record, `PROJECT_STATE.md`, and this compendium's
  timeline in one step.
- **Figure 1 of the SURA report** (published vs. reproduced grounding accuracy)
  was not rendered — the underlying numbers were recovered from the meeting Doc
  instead, and they match the report's claim.
- **The model family behind the grounding reproduction** (7B / 32B) is not
  recorded in any source seen.
- **No access to the raw trajectory data, screenshots, or the annotation viewer** —
  those live on Babel and in the running repo, not in Drive.
- **Amaad's icon-accuracy note is dated 2026-02-27 in the Doc**, which predates the
  project's May start. Recorded as-is; the date may be a doc artifact.
