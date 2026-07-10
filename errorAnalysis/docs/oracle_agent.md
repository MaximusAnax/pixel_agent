# OSWorld Human Agent (hybrid)

Operational doc for Phase 1D of the post–Phase 0 plan. Not a frozen grounding
file.

## What it is

An executor inside the OSWorld Docker/VM that replays OSWorld-Human
`human-ground-truth` actions and captures **observation screenshots before each
action**. Outputs feed:

1. **Annotators** — dual-trace review UI (human column)
2. **Judge** — multimodal provisional `osworld_v1` rejudge (non-binding reference)

It is **not** an OpenCUA model run, not training data, and **not** a gold path
the agent must match.

## Action tiers

| Tier | Examples | Executor |
|------|----------|----------|
| Deterministic | `` `HOTKEY` ``, `` `TYPING` ``, `` `PRESS` `` | Direct desktop control |
| Semi | `` `CLICK` cell G1 ``, sheet names | Parse + UI automation |
| Grounded | `` `CLICK` pivot table icon `` | Frontier VLM → coords → execute |

Audit before batch:

```bash
cd errorAnalysis
python scripts/audit_human_actions.py
```

## Artifacts

Per task (on Babel under mattlab shared tree for large PNGs):

```text
config/osworld/<pin>/oracle/<domain>/<task_id>/
  human_traj.json
  human_step_1_obs.png
  ...
  grounding_cache.jsonl
```

`human_traj.json` shape:

```json
{
  "task_id": "...",
  "domain": "chrome",
  "oracle_status": "ready|partial|failed",
  "steps": [
    {
      "step": 1,
      "action_text": "`HOTKEY` Ctrl+Shift+T",
      "action_tier": "deterministic",
      "observation_screenshot": "human_step_1_obs.png"
    }
  ]
}
```

`oracle_status`:

- `ready` — all steps executed; screenshots present
- `partial` — some grounded steps failed; ship available screenshots
- `failed` — unusable; keep text-only human ref in UI
- `pending` — not run yet

## Rejudge gate

`scripts/rejudge_pilot.py` skips episodes unless `oracle_status` is `ready` or
`partial`. Writes `failure_labels_osworld_v1.jsonl` — never overwrites prior
labels. Cost estimate (including human screenshot tokens) + Abdoul approval
required before a live batch.

## Status

- [x] Action parser + pilot action audit script
- [ ] Deterministic executor + grounded VLM executor on Babel
- [ ] `run_oracle_pilot.py` + sbatch
- [ ] Packet UI wiring (after mockup approval)
- [ ] Provisional `osworld_v1` rejudge
