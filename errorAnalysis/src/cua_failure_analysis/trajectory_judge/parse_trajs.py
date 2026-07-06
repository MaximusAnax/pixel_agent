"""Parse an unzipped OSWorld run into normalized failed-trajectory records.

Every run in this dataset is produced by OSWorld's `lib_run_single.py`, so each
<run_root>/.../<domain>/<task_id>/ holds:
  - result.txt        final reward (float; 0.0 = failure)
  - traj.jsonl        one JSON object per executed action (the step log)
  - step_{n}_{ts}.png the screenshot OBSERVED AFTER the n-th action executed
                      (it is `env.step(action)`'s returned obs, not a pre-action
                      shot; this dataset saves NO initial_state.png)
  - recording.mp4, runtime.log  (ignored here)

Each traj.jsonl record has the SAME top-level keys regardless of agent:
  {step_num, action_timestamp, action, response, reward, done, info,
   screenshot_file}
The only thing that varies is the *type* of `action`, which tells the two agents
apart, and that changes where the model's reasoning lives:

  OpenCUA-7B (data/trajs/turn_*):
    - `action`   : str -> a pyautogui call (or a terminal token DONE/FAIL).
    - `response` : str -> the FULL chain-of-thought, formatted as
                   "# Step N: ## Thought: ... ## Action: ... ## Code: ```...```".
                   This IS the reasoning. There is no `raw_response`.
    - stray lines shaped like {"Error": ...} (no step_num/action) are harness
      errors and are skipped.

  Claude-Sonnet-4.5 (data/trajs/results_claude-*):
    - `action`   : dict {action_type, command, id, input, name, raw_response}.
                   * `command`     -> the executed pyautogui call.
                   * `action_type` -> "tool_use", or a terminal token "DONE"/
                                      "FAIL" when there is no command.
                   * `input`       -> structured action, e.g.
                                      {"action":"left_click","coordinate":[x,y]}.
                   * `raw_response`-> the model's FULL output, tagged
                                      "[THINKING] ... [TEXT] ... [TOOL_USE] ...".
                                      The reasoning is here, NOT in `response`.
    - `response` : str -> ONLY the user-facing "[TEXT]" narration. It is a strict
                   subset of `raw_response`, so it must NOT be used as the
                   reasoning (that was the central bug in the old version).

Emits one normalized JSON record per FAILED trajectory to --out (append mode):
  {model, domain, task_id, instruction, reward, num_steps, steps:[{idx,
   screenshot_path, reasoning, action}]}

Usage (run once per run-root, appending). NOTE turn_1/turn_2/turn_3 are three
re-attempts of the SAME ~360 OpenCUA tasks; downstream dedups on
model/domain/task_id, so parse a single turn OR give each turn a distinct --model
label (e.g. opencua-7b-t1) to avoid uid collisions:
  python parse_trajs.py --run-root ../data/trajs/turn_1 --model opencua-7b \
      --osworld ../data/OSWorld/evaluation_examples/examples --out ../outputs/failures.jsonl
  python parse_trajs.py --run-root ../data/trajs/results_claude-sonnet-4-5-20250929_50steps \
      --model claude-sonnet-4.5 --out ../outputs/failures.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Both schemas share these top-level keys.
STEP_KEY = "step_num"
SHOT_KEY = "screenshot_file"

# Tagged segments inside Claude's `raw_response`. We keep the model's deliberation
# and any narration/infeasibility note, but drop the [TOOL_USE] trace because it
# just restates the action we already capture from `command`.
_RAW_SEG_RE = re.compile(r"\[([A-Z_]+)\]")
_DROP_SEGS = {"TOOL_USE"}


def stringify(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(v)


def clean_raw_response(raw: str) -> str:
    """Reduce Claude's `[THINKING]/[TEXT]/[TOOL_USE]` raw output to just the
    reasoning + narration, dropping the redundant tool-call trace. Keeps the tags
    only when more than one segment survives, so the common text-only step reads
    cleanly instead of being prefixed with a lone "[TEXT]"."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    matches = list(_RAW_SEG_RE.finditer(raw))
    if not matches:
        return raw
    kept: list[tuple[str, str]] = []
    pre = raw[: matches[0].start()].strip()
    if pre:
        kept.append(("", pre))
    for i, m in enumerate(matches):
        tag = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[m.end():end].strip()
        if tag in _DROP_SEGS or not body:
            continue
        kept.append((tag, body))
    if not kept:
        return ""
    if len(kept) == 1:
        return kept[0][1]
    return "\n".join(f"[{tag}] {body}" if tag else body for tag, body in kept).strip()


def extract_reasoning(rec: dict) -> str:
    """The model's thinking. For Claude it is in action.raw_response; for OpenCUA
    it is the top-level `response`."""
    action = rec.get("action")
    if isinstance(action, dict):
        reasoning = clean_raw_response(action.get("raw_response") or "")
        # Terminal steps (DONE/FAIL) may carry no raw_response; fall back to the
        # user-facing narration so the step isn't blank.
        return reasoning or stringify(rec.get("response"))
    return stringify(rec.get("response"))


def extract_action(rec: dict) -> str:
    """Concise, judge-friendly action string."""
    action = rec.get("action")
    if isinstance(action, str):
        return action.strip()  # OpenCUA: pyautogui call or DONE/FAIL token
    if isinstance(action, dict):
        cmd = (action.get("command") or "").strip()
        if cmd:
            return cmd
        # No command -> a terminal/control signal lives in action_type.
        at = action.get("action_type")
        if at and at != "tool_use":
            return str(at)  # DONE / FAIL / INFEASIBLE
        # Last resort: the structured tool input.
        inp = action.get("input")
        return stringify(inp) if inp not in (None, "", {}, []) else ""
    return ""


def is_step_record(rec: dict) -> bool:
    """True for a real agent step; False for harness rows like {"Error": ...}."""
    if not isinstance(rec, dict):
        return False
    if STEP_KEY in rec:
        return True
    # Be lenient if step_num is ever missing, but still reject pure error rows.
    return ("action" in rec or "response" in rec) and "Error" not in rec


def read_reward(task_dir: Path) -> float | None:
    rt = task_dir / "result.txt"
    if not rt.exists():
        return None
    try:
        return float(rt.read_text().strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


def load_instructions(osworld_examples: Path | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not osworld_examples or not osworld_examples.exists():
        return mapping
    for jf in osworld_examples.rglob("*.json"):
        try:
            d = json.loads(jf.read_text())
        except Exception:  # noqa: BLE001
            continue
        tid = d.get("id") or jf.stem
        if "instruction" in d:
            mapping[tid] = d["instruction"]
    return mapping


def find_traj_file(task_dir: Path) -> Path | None:
    for name in ("traj.jsonl", "trajectory.jsonl"):
        if (task_dir / name).exists():
            return task_dir / name
    jsonls = sorted(task_dir.glob("*.jsonl"))
    return jsonls[0] if jsonls else None


def parse_steps(task_dir: Path) -> list[dict]:
    steps: list[dict] = []
    # Optional pre-action observation. This dataset doesn't save one, but keep the
    # guarded check so the parser stays correct for runs that do.
    init = task_dir / "initial_state.png"
    if init.exists():
        steps.append({"idx": 0, "screenshot_path": str(init),
                      "reasoning": "(initial desktop state)", "action": "(none)"})

    tf = find_traj_file(task_dir)
    if tf is not None:
        with tf.open() as f:
            fallback_idx = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not is_step_record(rec):
                    continue
                fallback_idx += 1
                raw_idx = rec.get(STEP_KEY)
                idx = int(raw_idx) if isinstance(raw_idx, (int, float)) else fallback_idx
                shot = rec.get(SHOT_KEY)
                shot_path = None
                if shot:
                    cand = task_dir / Path(str(shot)).name
                    shot_path = str(cand) if cand.exists() else None
                steps.append({
                    "idx": idx,
                    "screenshot_path": shot_path,
                    "reasoning": extract_reasoning(rec),
                    "action": extract_action(rec),
                })

    # Fallback: no traj records but screenshots exist -> skeleton from images.
    if len(steps) <= (1 if init.exists() else 0):
        shots = sorted(task_dir.glob("step_*.png"))
        for j, s in enumerate(shots, start=1):
            steps.append({"idx": j, "screenshot_path": str(s),
                          "reasoning": "", "action": "(action log unavailable)"})
    return steps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--model", required=True, help="label for this run, e.g. opencua-7b")
    ap.add_argument("--osworld", default="../data/OSWorld/evaluation_examples/examples")
    ap.add_argument("--out", default="../outputs/failures.jsonl")
    ap.add_argument("--only-failures", action="store_true", default=True)
    ap.add_argument("--include-all", dest="only_failures", action="store_false",
                    help="also include successful trajectories")
    args = ap.parse_args()

    run_root = Path(args.run_root)
    instructions = load_instructions(Path(args.osworld))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    task_dirs = [p.parent for p in run_root.rglob("result.txt")]
    print(f"[{args.model}] {len(task_dirs)} task dirs under {run_root}")

    n_written = 0
    per_domain: dict[str, int] = {}
    missing_instr = 0
    with out_path.open("a") as fout:
        for td in task_dirs:
            reward = read_reward(td)
            if reward is None:
                continue
            if args.only_failures and reward != 0.0:
                continue
            domain = td.parent.name
            task_id = td.name
            steps = parse_steps(td)
            instr = instructions.get(task_id)
            if instr is None:
                missing_instr += 1
                instr = "(instruction not found in OSWorld examples)"
            rec = {
                "model": args.model, "domain": domain, "task_id": task_id,
                "instruction": instr, "reward": reward,
                "num_steps": sum(1 for s in steps if s["idx"] > 0),
                "steps": steps,
            }
            fout.write(json.dumps(rec) + "\n")
            n_written += 1
            per_domain[domain] = per_domain.get(domain, 0) + 1

    print(f"[{args.model}] wrote {n_written} trajectories "
          f"({'failures only' if args.only_failures else 'all'}). "
          f"Missing instruction: {missing_instr}.")
    for d in sorted(per_domain):
        print(f"    {d}: {per_domain[d]}")
    print(f"-> appended to {out_path}")


if __name__ == "__main__":
    main()
