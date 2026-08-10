# Human reference artifacts (partner handoff)

Operational consumer contract for OSWorld-Human screenshots used by the
review UI and provisional multimodal `osworld_v1` rejudge.

**We do not run** OSWorld VMs or a Human Agent executor in this repo. A research
partner produces `human_traj.json` + observation PNGs on Babel under the shared
mattlab project tree. Exact directory TBD — once known, pass it as
`--oracle-root` (or set `ORACLE_ROOT`) when building the review packet or
running `scripts/rejudge_pilot.py`.

## Layout

Either nested or flat under the oracle root:

```text
<oracle-root>/
  <domain>/<task_id>/
    human_traj.json
    human_step_1_obs.png
    human_step_2_obs.png
    ...
```

or:

```text
<oracle-root>/
  <task_id>/
    human_traj.json
    human_step_N_obs.png
    ...
```

`scripts/rejudge_pilot.py` and the packet builder resolve
`<oracle-root>/<domain>/<task_id>/` first, then `<oracle-root>/<task_id>/`.

## `human_traj.json` schema

```json
{
  "task_id": "06fe7178-4491-4589-810f-2e2bc9502122",
  "domain": "chrome",
  "oracle_status": "ready|partial|failed",
  "steps": [
    {
      "step": 1,
      "action_text": "`HOTKEY` Ctrl+Shift+T",
      "observation_screenshot": "human_step_1_obs.png",
      "ok": true
    }
  ]
}
```

Accepted aliases (loader is tolerant):

| Field | Also accepted |
|-------|----------------|
| `steps` | `human_steps` |
| `action_text` | `action` |
| `observation_screenshot` | `image_path` (relative to the traj dir, or absolute) |

`oracle_status`:

| Value | Meaning |
|-------|---------|
| `ready` | All steps usable; screenshots present |
| `partial` | Some steps/screenshots missing; still usable for UI + gated rejudge |
| `failed` | Nothing usable — skip for multimodal rejudge |
| `pending` | Not produced yet (default when traj missing) |

## Consumers in this repo

1. **Review packet** — human reference drawer (text from vendored OSWorld-Human
   when screenshots absent; PNGs when `oracle_status` is `ready`/`partial`).
2. **Judge** — `load_human_reference_steps` in
   `src/cua_failure_analysis/attribution/pipeline.py`;
   `scripts/rejudge_pilot.py` skips episodes unless status is `ready` or
   `partial`. Writes `failure_labels_osworld_v1.jsonl` only — never overwrites
   prior label files.

## Non-binding contract

The full human trajectory (text + screenshots) is a **viable reference path**,
not the only valid path. Annotators and the judge must not overfit to it; agent
actions that diverge can still be correct if they progress toward OSWorld
success criteria. UI and prompts treat human length as **decoupled** from the
agent timeline (no forced step alignment).

## Wiring when the partner path is known

```bash
# on Babel / local packet rebuild
export ORACLE_ROOT=/data/group_data/mattlab/pixel_agent/<partner>/oracle   # TBD
python scripts/build_trace_review_packet.py ... --oracle-root "$ORACLE_ROOT"
# or refresh existing packet HTML + stage PNGs into episode/human/:
python scripts/refresh_review_packet_html.py <packet_id> --oracle-root "$ORACLE_ROOT"
```

```bash
# cost gate (Abdoul OK) then provisional rejudge — never overwrites prior labels
python scripts/estimate_judge_cost.py --run-dir <run>   # include image budget for human obs
python scripts/rejudge_pilot.py --run-dir <run> --oracle-root "$ORACLE_ROOT"
# → <run>/failure_labels_osworld_v1.jsonl
```

Until `ORACLE_ROOT` is set, UI shows vendored human **text** and oracle badge
`pending`; rejudge remains gated.

Schema spot-check (CI): `tests/test_oracle_handoff.py` covers task
`06fe7178-4491-4589-810f-2e2bc9502122` nested layout + dry-run rejudge gate.
