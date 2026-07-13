# goldTrajectories — operating contract

## What this stage validates

Generate **gold (reference) trajectories** for OSWorld tasks: run a compute-use
agent that only has to **ground** actions (not plan them), guided by the
**OSWorld-Human** dataset's ordered action sequences, capture the resulting
screenshots + actions, and keep the runs the OSWorld evaluator marks **correct**.
These verified trajectories become a reference rubric for judging *other* agents
(e.g. the `errorAnalysis/` whole-trajectory judge) that attempted the same tasks
**without** guidance.

Pipeline: OSWorld-Human step (`` `CLICK` address bar ``) → grounding model
(**UGround-V1-7B**, local vLLM on a 48 GB GPU) → pixel action → execute in a live
OSWorld VM → screenshot → OSWorld evaluator verdict → keep if passed.

## Role for this stage

Unlike Phase-1 `errorAnalysis/` (ops-only, "do NOT run new trajectories"), this
stage **is explicitly authorized by Raghav to run new OSWorld trajectories**.
Agents may stand up the environment and run guided replays. Still evidence-first:
only evaluator-verified runs count as gold.

## Non-negotiable boundaries

- **Local/open models only** for the agent — no closed-model API credits for
  generation (UGround / OpenCUA class on Babel GPUs). API models are allowed only
  for *downstream judging*, not for producing gold trajectories.
- Keep large assets (SIF, qcow2, HF caches, per-run scratch) **out of the repo**
  and off `$HOME`; they live under `/data/group_data/mattlab/raghavg3/osworld_env/`.
- A trajectory is **gold only if the OSWorld task evaluator passes** it. Never
  label a run gold from screenshots alone.
- Don't run large/expensive GPU sweeps without Raghav's approval of the reason;
  calibrate on a few tasks first (spike → smoke → scale).
- Never mutate the base `Ubuntu.qcow2`; always boot a disposable overlay.
- Don't reconcile taxonomies or overwrite `errorAnalysis/` outputs.

## Environment ground truth (Babel)

- OSWorld VM runs under **Apptainer + QEMU/KVM** (no Docker). `/dev/kvm` is
  available on compute nodes. Networking is **user-mode SLIRP + hostfwd** to
  avoid needing NET_ADMIN. Recipe + rationale: `docs/spike_plan.md`.
- The guest control server is HTTP on `:5000`; `DesktopEnv` drives it. A small
  `manual` provider points `DesktopEnv` at an already-running VM.
- Prefer a 48 GB GPU (`--gres=gpu:L40S:1`) for the grounding model; the VM itself
  is CPU+KVM only (`--partition cpu`), so the two can run as separate jobs that
  talk over HTTP.

## Default flow

1. One-time assets (login/compute node with egress): pull SIF, download+unzip
   `Ubuntu.qcow2`, build venv, clone OSWorld. See `docs/spike_plan.md`.
2. **Spike (Phase A):** `scripts/spike_phase_a.sbatch` — boot VM, prove
   screenshot→action→screenshot. Artifacts in `$osworld_env/run/<job>/phase_a/`.
3. **Spike (Phase B):** one task via `DesktopEnv.reset()` + `.evaluate()` through
   the `manual` provider.
4. **Guided replay (later):** serve UGround-V1-7B (vLLM), replay OSWorld-Human
   steps per task, write gold traces in the `errorAnalysis` trace schema
   (`<model>/<task>/<seed>/{trace.jsonl,manifest.json}` + PNGs), keep only passes.

## Outputs convention

Compact per-run summaries to `goldTrajectories/data/<backend>_outputs/<run_id>/summary.md`.
Gold traces (screenshots + actions) live under the external `osworld_env/` asset
tree and are referenced by manifest, not committed.

## Multi-agent notes

Env (CPU+KVM) and grounding server (GPU) are independent SLURM jobs; never block
one agent on another's cluster wait — poll via `sacct`/background. Pass absolute
paths; subagents start with no history.
