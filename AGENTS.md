# pixelAgent — Project Brain

This is the root context for the **pixelAgent** research program on
computer-use agents (CUA). It is loaded at the start of every Hermes session
rooted here, so it holds the **durable, cross-cutting** picture of the whole
project. Stage-specific detail lives in each subdirectory's own `AGENTS.md`,
which Hermes loads automatically as it works inside that subdirectory.

> Read this for orientation and shared rules; defer to the active stage's
> `AGENTS.md` for the authoritative contract on that work.

## Structure (grows over time)

`pixelAgent/` is organized as a multi-stage research program. Each idea or phase
gets its own top-level subdirectory with its own `AGENTS.md`. Over time this will
include stages such as experimentation, implementation, and evaluation of
particular ideas — not just the current one.

| Stage / subdir   | Purpose                                                                                     | Status  | Contract                          |
| ---------------- | ------------------------------------------------------------------------------------------- | ------- | --------------------------------- |
| `errorAnalysis/` | Phase 1: failure analysis of low-parameter CUA agents on OSWorld, run remotely on CMU Babel | Active  | `errorAnalysis/AGENTS.md`         |
| *(future)*       | e.g. `experimentation/`, `implementation/`, `evaluation/` of a given idea                   | Planned | add one when the stage is created |

When a new stage is added: create the subdirectory and give it an `AGENTS.md`
describing its scope, commands, and conventions. Add a row above. Keep this root
file about what is shared across stages, not the specifics of any one.

## Mission

Build rigorous, evidence-backed understanding of how and why computer-use agents
(especially small models) fail, and turn that into reusable methodology. The
human researcher is **Abdoul**; Hermes is the research-operations agent that helps
move the work forward and explains its reasoning so Abdoul learns the system.

## Project-wide principles (apply to every stage)

- Evidence over confident guesses; separate raw evidence, attribution, and
  interpretation, and flag uncalibrated interpretation as provisional.
- Prefer remote/cluster computation over hoarding large data locally.
- Produce small, inspectable artifacts over raw-data piles.
- Favor fast calibration loops over premature large-scale sweeps.
- Don't run large/expensive compute (e.g. GPU jobs) without Abdoul approving the reason.
- Never overwrite prior results, and never change a stage's core definitions
  (taxonomies, protocols) without Abdoul's explicit approval.

## Active stage: errorAnalysis

Currently the only stage. Full operating contract: **`errorAnalysis/AGENTS.md`**.
Critical boundaries for this stage (so even a first message is safe):

- Never download OSWorld-Verified trajectory zips to the laptop; analysis runs
  remotely on CMU Babel.
- Never mirror the full Hugging Face dataset (~480GB).
- Never use `/home/andiongu` on Babel for large zips, traces, or HF caches.
- Never treat best-effort adapter labels as final scientific labels.
- Never modify `errorAnalysis/failureTaxonomy.md` without Abdoul's approval.

Entry points:

- Operating contract: `errorAnalysis/AGENTS.md`
- Run via Hermes (setup): `errorAnalysis/docs/hermes_setup.md`
- Babel workflow detail: `errorAnalysis/docs/babel_hf_orchestration.md`
- Runnable skill: `babel-osworld-analysis` (installed under `~/.hermes/skills/`)

Run that stage's commands from `errorAnalysis/` (its scripts, config, and
`config/babel.env` live there).
