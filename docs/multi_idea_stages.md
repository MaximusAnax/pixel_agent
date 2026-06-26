# Multi-idea stages — protocol for future agents

> **Audience:** Cursor, Hermes, and any agent working in this repo.
> **Read this when:** Abdoul (or the team) adds a second top-level idea directory,
> asks Hermes to run validation experiments from multiple subdirs, or moves toward
> closed-loop / autoresearch orchestration across ideas.
> **Do not implement ahead of need** — this doc is the contract for when that time
> comes. Until then, `errorAnalysis/` remains the only executable stage.

## Layout (already decided)

```text
pixelAgent/                    ← git root; root AGENTS.md = program brain + live state
├── ops/                       ← cross-stage ONLY (reports, meetings, PROJECT_STATE)
├── docs/                      ← program-wide design docs (this file)
├── hermes/skills/             ← cross-stage Hermes skills (e.g. project-state-sync)
└── <ideaName>/                ← one top-level dir per distinct experiment / validation track
    ├── AGENTS.md              ← Hermes operating contract for THIS idea (required)
    ├── config/                ← git-ignored *.env from *.env.example
    ├── scripts/               ← submit, poll, sync, local runners
    ├── data/                  ← run outputs; use <idea>/data/.../summary.md convention
    ├── hermes/skills/         ← idea-specific skills (e.g. babel-osworld-analysis)
    └── docs/                  ← runbooks for this idea
```

**Rules that must not drift:**

| Layer | Owns | Must NOT own |
| --- | --- | --- |
| **Repo root** | `AGENTS.md` live state, `ops/`, program principles, stage registry table | Idea-specific submit scripts, cluster paths, taxonomies |
| **`<idea>/`** | Job execution, boundaries, skills, `data/` artifacts | Weekly reports, meeting ingest, root PROJECT_STATE synthesis |

Reference implementation: **`errorAnalysis/`** — copy its *shape*, not its Babel/OSWorld specifics.

## When to spin up a new `<idea>/` directory

Create a new top-level idea stage when **all** apply:

1. The work has a **distinct hypothesis or validation goal** (not just a sub-task of an existing idea).
2. It needs its own **boundaries** (what Hermes must never do for this idea).
3. It will produce its own **`data/` run artifacts** and possibly its own remote jobs.
4. Abdoul (researcher) has agreed the idea deserves a persistent track in the repo.

Do **not** create a new top-level dir for: one-off scripts, a single PR, or a subfolder that clearly belongs inside an existing idea.

## Checklist — adding idea `#N` (for Cursor / Hermes)

When Abdoul approves a new idea stage, an agent should:

1. **Create `<ideaName>/`** using the layout above (mirror `errorAnalysis/` structure at a high level).
2. **Write `<ideaName>/AGENTS.md`** with:
   - what the idea validates;
   - Hermes role (ops-only vs allowed to propose/run experiments);
   - non-negotiable boundaries;
   - default flow (numbered steps, exact script paths);
   - multi-agent notes (`delegate_task`, absolute paths, async poll pattern).
3. **Add a Hermes skill** at `<ideaName>/hermes/skills/<skill-name>/SKILL.md` if the default flow is non-trivial (see `errorAnalysis/hermes/skills/babel-osworld-analysis/`).
4. **Update root `AGENTS.md`:**
   - add a row to the Structure table;
   - replace or extend "Active stage" language so multiple ideas can be listed;
   - do **not** move idea-specific commands into root `AGENTS.md`.
5. **Outputs convention:** write compact run summaries to  
   `<ideaName>/data/<backend>_outputs/<run_id>/summary.md`  
   (or document a different path in that idea's `AGENTS.md`). Root `ops/weekly_report.py` already globs `*/data/babel_outputs/*/summary.md` — extend the glob or registry if the new idea uses a different output layout (see below).
6. **Run `python ops/synthesize_state.py`** after the first meeting notes or run that mention the new idea, so root live state reflects it.
7. **Do not** duplicate root `ops/` into the new idea. **Do not** put the new idea's live-state block in `<idea>/AGENTS.md` — only root `AGENTS.md` carries the managed `PROJECT_STATE` block.

Ask Abdoul before: large GPU spend, new taxonomies/protocols, or changing root project principles.

## Hermes orchestration across multiple ideas

**Parent session (repo root or VPS):**

- Loads root `AGENTS.md` + `ops/state/PROJECT_STATE.md`.
- Plans which idea(s) need work this week.
- Uses **`delegate_task`** — one subagent per idea/job, `toolsets=["terminal","file"]`.
- Passes each child: **absolute paths**, **exact commands**, and a pointer to **that idea's `AGENTS.md`** (subagents have no shared history).
- Uses **cron / background terminal** for long polls (Slurm, etc.) — never block a subagent on cluster waits.

**Child session (inside `<idea>/`):**

- `cd` into the idea directory (or use absolute paths to its scripts).
- Follow **only** that idea's `AGENTS.md` for boundaries and default flow.
- Return: run id, paths to artifacts, next smallest action.

**Cursor (IDE agent):** same split — program-wide edits at repo root; idea-specific code and scripts under `<idea>/`. When editing orchestration, read root `AGENTS.md` first, then the active idea's `AGENTS.md`.

## Evolving root memory for multiple ideas (when needed)

Not required for idea #1. When **two or more** ideas are active, extend (do not rewrite from scratch):

| Component | Extension |
| --- | --- |
| `ops/state/PROJECT_STATE.md` | Per-idea sections (status, last run, open questions) |
| Root `AGENTS.md` live block | Digest per active idea, not only global progress |
| `ops/synthesize_state.py` | Tag meeting notes / runs by idea name when present |
| `ops/weekly_report.py` | Already scans all `*/data/.../summary.md`; add patterns or `ops/registry/runs.jsonl` if ideas diverge |

Optional later: append-only **`ops/registry/runs.jsonl`** (`idea`, `run_id`, `status`, `path`, `timestamp`) so Hermes can choose next work without scanning the tree. Add only when manual globbing breaks down.

## Roadmap hook (autoresearch)

This doc supports steps 4–5 in `docs/project_state_automation.md`:

- **Closed experiment loop** — each idea's skill submits jobs; root `ops/` ingests results into PROJECT_STATE.
- **Autoresearch** — parent Hermes at root proposes experiments from PROJECT_STATE; Abdoul approves; children execute per-idea `AGENTS.md`.

Human approval gates stay until explicitly relaxed in root `AGENTS.md`.

## Anti-patterns (future agents: avoid)

- Putting experiment runners in root `ops/` (root `ops/` observes; ideas execute).
- One `AGENTS.md` at root with all Babel/Slurm detail for every idea (unmaintainable; boundaries leak).
- Hermes subagents without absolute paths (they will lose context and break paths).
- Blocking `delegate_task` on cluster job completion (use `wait_for_run.sh`, cron, or background terminal).
- Creating a new top-level dir without updating root `AGENTS.md` structure table (orchestration blind spot).
