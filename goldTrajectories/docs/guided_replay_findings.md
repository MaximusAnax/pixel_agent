# Guided grounded-replay — pipeline and findings

## What works (verified)

End-to-end guided grounded replay runs locally on Babel and produces an
**evaluator-verified** completion:

- **First verified pass:** task `b148e375` *"add a new layer named 'Square'"* —
  OSWorld evaluator `score = 1.0`, `success = true` (SLURM job on a `general`
  L40S node). Steps: `Shift+Ctrl+N` → type `Square` → `Enter`.

Architecture (one GPU node, all localhost):
- **UGround-V1-7B** grounding server (`scripts/ug_server.py`, venv-ground):
  screenshot + referring expression → pixel point ([0,1000)→px).
- **OSWorld VM** under Apptainer+QEMU/KVM (`scripts/launch_vm.sh`), VNC optional.
- **Replay driver** (`scripts/replay_agent.py`, venv-osworld py3.12, under
  `xvfb-run`): parses OSWorld-Human `single-action` steps, grounds each CLICK,
  executes TYPING/PRESS/HOTKEY/MOVE_TO via `DesktopEnv` (manual provider), then
  runs the OSWorld evaluator. A run is gold only if the evaluator passes.
- Orchestrated by `scripts/demo_task.sbatch` with a GO-gate for live watching.

## Findings (important for the gold-trajectory methodology)

1. **UGround-V1-7B is imprecise on small, densely-packed targets.** It grounds
   large, text-labeled web/UI elements well, but on GIMP's menu bar it missed
   "Filters" by ~30 px and hit the adjacent "Windows" menu; middle dock icons
   were similarly off (edges — Activities/clock/Trash — were correct). Menu- and
   toolbar-heavy tasks need finer grounding → **UGround-V1-72B** (Babel A100-80GB
   / H200, vLLM tensor-parallel) is the recommended upgrade for those.

2. **OSWorld-Human guidance can drift from the VM's current UI.** Task
   `bb5e4c0d` (make Bing default) describes a Chrome "search engine dropdown +
   radio button", but the VM's current Chrome shows a "Change" button + dialog.
   The terse steps no longer map. Gold generation needs either UI-version-matched
   VMs or per-task drift handling.

3. **Unexpected startup modals** not in the human demo block replay (GIMP's
   "Convert to RGB working space?" color-profile prompt). The driver now presses
   Escape after reset to dismiss such modals generically.

4. **Browser omnibox input is fragile**: synthetic keystrokes can double the
   first char, and inline autocomplete (".../search" → ".../searchEngines") is
   accepted by Enter. The driver focuses the omnibox with Ctrl+L and, for URLs,
   clears the field + strips autocomplete before Enter.

## Task-selection guidance for reliable gold generation (7B)

Prefer tasks with: stable UIs (GIMP/LibreOffice/GNOME over drift-prone browser
settings), few steps, and targets that are either keyboard-addressable (hotkeys)
or large/well-separated. Menu-navigation and small-cell tasks want 72B grounding.

## 72B smoke test (2026-07-14, 6 tasks, 2 shards)

UGround-V1-72B served on 4x L40S (transformers `device_map=auto`, `ug_server.py`);
batch via `run_batch.sbatch` against a shared remote server. **4/6 gold**
(evaluator score 1.0): GIMP add-layer (regression), **GIMP Vignette a746add2 —
the menu task 7B failed**, VS Code create-file, GNOME text-scaling. Two content
failures: GIMP undo-prefs `7b7617bd` (dense Preferences dialog) and VLC cone
`215dfd39` (grounded screen-center fallback → likely UI drift vs. the human demo).

Infra lessons baked into the scripts:
1. `device_map=auto` packs GPU 0 full → cap per-GPU `max_memory` with headroom
   (extra on GPU 0: vision tower + embeddings live there).
2. **`attn_implementation="sdpa"`, never eager**: eager materializes the full
   vision-attention matrix (~10k patch tokens at 1080p → 6+ GiB softmax → OOM).
3. Generation is serialized behind a lock; concurrent shards queue (~22–27 s per
   1080p grounding call).
4. OSWorld-Human hotkey text carries prose ("ctrl-alt-t to open terminal") —
   `parse_hotkey` extracts the combo.
5. Failed manifests no longer block retries (skip only `success: true`).

## Next steps

- Add per-task UI-drift overrides for known-drifted tasks (e.g. `215dfd39`).
- Scale to the pilot set, writing gold traces in the errorAnalysis trace schema,
  keeping only evaluator-verified passes. Needs Raghav's go for the full
  369-task sweep (~4 L40S for the server + cpu-partition shard array).
