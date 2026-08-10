# Oracle Agent — replaying human trajectories for per-step gold screenshots

**Status:** design + offline scaffold (idea branch — needs Abdoul's approval
to become a track). Scoped in the 2026-08-07 meeting: *"replay human actions
in OpenCUA to generate a screenshot for every human step."*

## Why (and why now)

The 2026-08-10 SOTA scan (`docs/research/2026-08-10_small_cua_sota_and_open_questions.md`
§5) found **no published system that replays OSWorld human demonstrations
action-by-action to regenerate per-step screenshots for grounding-vs-planning
failure attribution**. Nearest neighbors are components, not integrations:
OSWorld-Human (steps, no replay harness), PC Agent-E "Trajectory Boost"
(replayed human states for *training data*, Windows), AgentNetBench
(teacher-forced offline eval along human demos), WebCanvas key nodes
(checkpoints). The integration is open ground.

What it buys Phase 1:

1. **Gold-label substrate.** Every human step gets a screenshot + state, so
   annotators (and the judge) can label agent divergence against a concrete
   visual reference instead of imagining it — directly serving the
   inter-annotator study and judge protocol v2 (reference trajectory).
2. **Teacher-forced small-model eval.** Feed the human prefix (screenshots +
   actions) to OpenCUA/GUI-Owl-class models and score the next action —
   isolates perception/grounding from compounding planning drift, the causal
   arm the novelty scan recommends.
3. **Divergence-point detection.** First step where the agent's action
   distribution leaves the human path ≈ a principled `t*` candidate,
   cross-checkable against `find_first_failure_step`.
4. **Fixes the three gold-label blockers from the meeting:** incomplete
   OSWorld-Human steps (replay exposes them deterministically → patch list),
   racing ahead of a loading screen (replay waits for screen-stability
   between actions — see §Stability), and init errors (post-reset
   verification hook before any action).

## Architecture

```text
OSWorld-Human trajectory (JSON)                 [adapter: verify real schema]
   -> normalize_actions() -> [OracleAction]     (pure, unit-tested, offline)
   -> ReplaySession(env).run()                  (on Babel/AWS OSWorld VM)
        for each action:
          screenshot_before -> data/oracle/<task>/<step>/screen.png
          execute (pyautogui code string via env.step)
          wait_until_stable(hash-diff poll, timeout)   # anti-racing
          log TraceStep (existing cua_failure_analysis schema)
   -> manifest.json + trace.jsonl  (drop-in for attribution + autoResearch)
```

- **Action normalization** accepts the loose dict shapes seen in OSWorld-ish
  trajectory dumps (`type`/`action`, `coordinate`/`x,y`, `text`, `key(s)`,
  scroll params) and emits canonical `OracleAction`s that render to OSWorld's
  `pyautogui` code-string action space. The OSWorld-Human adapter must be
  validated against the real dataset schema on Babel (HF was unreachable
  from the sandbox that authored this).
- **Init verification** (`--verify-init`): after `env.reset`, capture a
  screenshot and (when the a11y tree is available) assert expected apps are
  present; abort with a typed `init_error` instead of producing a corrupted
  trace — Raghav's initialization-bug ticket gets data instead of anecdotes.
- **Stability wait:** poll screenshots at `--poll-interval`, proceed when two
  consecutive frame hashes match or `--stabilize-timeout` hits (recorded per
  step, so "screen still loading" becomes measurable rather than a race).
- **Incomplete-step detection:** replay evaluates the task after the final
  human action; a failing evaluator on a "successful" human trajectory flags
  an incomplete OSWorld-Human annotation (e.g. typed but never pressed
  Enter) → emit `incomplete_step_report.json` patch candidates.

## Interfaces

- Output uses the existing `TraceStep`/`RunManifest` schema
  (`cua_failure_analysis.trace.schema`) with `model_id="human-oracle"`, so
  attribution, stats, and the autoResearch eval-set builder consume it
  unchanged.
- `reference_summary` for judge protocol v2 can then be generated from real
  replayed steps instead of hand-written summaries.

## Staged plan

| Stage | What | Where | Exit |
|---|---|---|---|
| O0 | Offline scaffold: normalization + dry-run planner + tests | this branch | `pytest` green; dry-run renders a full action script for a sample trajectory |
| O1 | Schema adapter vs real OSWorld-Human dump; replay 3 tasks manually watched | Babel/AWS VM | 3 tasks fully replayed; screenshots per step; incomplete-step report works |
| O2 | Batch replay of the ~10-trace annotation set; wire into labeling CSVs | Babel | annotators label with per-step gold screenshots |
| O3 | Teacher-forced next-action eval for OpenCUA-7B / GUI-Owl-1.5 | Babel | per-step divergence table; feeds prevalence + judge calibration |

Compute note: replay is CPU/VM-bound (no GPU) except O3 inference; still needs
Abdoul's approval per root AGENTS.md before any cluster runs.

## Run (once on OSWorld infra)

```bash
# dry run — no environment needed, validates + prints the action plan:
python scripts/oracle_replay.py --trajectory path/to/human_traj.json --dry-run

# real replay on a machine with OSWorld installed:
python scripts/oracle_replay.py --trajectory human_traj.json \
    --task-config path/to/osworld_task.json --out data/oracle/<task_id> \
    --verify-init --stabilize-timeout 10
```
