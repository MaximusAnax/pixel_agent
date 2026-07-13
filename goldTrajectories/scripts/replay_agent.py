#!/usr/bin/env python3
"""OSWorld-Human guided grounded-replay agent (runs in venv-osworld, under xvfb-run).

For one OSWorld task, replay the OSWorld-Human `human-ground-truth` action sequence:
each semantic step (`` `CLICK` the address bar ``) is *grounded* by UGround into a
pixel target, executed in the live VM via DesktopEnv, and screenshotted. After the
sequence, the OSWorld evaluator returns pass/fail. A run counts as a gold trajectory
only if the evaluator passes. Output mirrors the errorAnalysis trace schema.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import requests

VERB_RE = re.compile(r"^`([A-Z_]+)`\s*(.*)$")
CLICK_VERBS = {"CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "MOVE", "HOVER", "DRAG", "LEFT_CLICK"}


def parse_step(s: str):
    m = VERB_RE.match(s.strip())
    if not m:
        return None, s.strip()
    return m.group(1), m.group(2).strip()


def first_quoted(s: str):
    m = re.search(r"'([^']*)'", s) or re.search(r'"([^"]*)"', s)
    return m.group(1) if m else None


KEYMAP = {"del": "delete", "esc": "escape", "return": "enter", "ctrl": "ctrl"}


def norm_key(k: str) -> str:
    k = k.strip().lower()
    return KEYMAP.get(k, k)


def ground(ug_url: str, png: bytes, description: str) -> dict:
    r = requests.post(ug_url + "/ground",
                      json={"image": base64.b64encode(png).decode(), "description": description},
                      timeout=180)
    r.raise_for_status()
    return r.json()


def build_action(verb: str, rest: str, ground_pt):
    """Return (pyautogui_command, coords_or_None)."""
    if verb in CLICK_VERBS:
        x, y = ground_pt
        fn = {"CLICK": "click", "LEFT_CLICK": "click", "DOUBLE_CLICK": "doubleClick",
              "RIGHT_CLICK": "rightClick", "MOVE": "moveTo", "HOVER": "moveTo",
              "DRAG": "click"}.get(verb, "click")
        cmd = (f"import pyautogui, time; pyautogui.moveTo({x}, {y}, duration=0.6); "
               f"time.sleep(0.3); pyautogui.{fn}(" + ("" if fn == "moveTo" else f"{x}, {y}") + ")")
        return cmd, (x, y)
    if verb == "TYPING":
        text = first_quoted(rest)
        text = text if text is not None else rest
        return f"import pyautogui; pyautogui.typewrite({text!r}, interval=0.04)", None
    if verb == "PRESS":
        key = norm_key(first_quoted(rest) or rest)
        return f"import pyautogui; pyautogui.press({key!r})", None
    if verb in ("HOTKEY", "KEY"):
        combo = first_quoted(rest) or rest
        keys = [norm_key(k) for k in re.split(r"[+\s]+", combo) if k.strip()]
        return f"import pyautogui; pyautogui.hotkey(*{keys!r})", None
    if verb == "SCROLL":
        amt = -300 if "down" in rest.lower() else 300
        return f"import pyautogui; pyautogui.scroll({amt})", None
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-file", required=True)
    ap.add_argument("--ug-url", default="http://127.0.0.1:8500")
    ap.add_argument("--vm-host", default="127.0.0.1")
    ap.add_argument("--vm-port", type=int, default=5000)
    ap.add_argument("--stage-dir", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--settle", type=int, default=30)
    ap.add_argument("--step-pause", type=float, default=2.0)
    ap.add_argument("--model-id", default="uground-7b-guided")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(args.stage_dir) / "src"))
    from osworld_manual_provider import install
    install(host=args.vm_host, server_port=args.vm_port)
    from desktop_env.desktop_env import DesktopEnv

    task = json.loads(Path(args.task_file).read_text())
    steps = task["human-ground-truth"]["single-action"]
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)
    shots = out / "screenshots"; shots.mkdir(exist_ok=True)

    print(f"[replay] task {task['id']}: {task['instruction']}", flush=True)
    print(f"[replay] {len(steps)} human steps", flush=True)

    env = DesktopEnv(provider_name="docker", action_space="pyautogui",
                     require_a11y_tree=False, require_terminal=False,
                     cache_dir=str(out / "cache"), headless=True)
    print("[replay] resetting task (running setup config) ...", flush=True)
    obs = env.reset(task_config=task)
    time.sleep(args.settle)  # let apps finish painting
    obs = env._get_obs()

    trace = []
    for i, step in enumerate(steps):
        verb, rest = parse_step(step)
        before = obs["screenshot"]
        (shots / f"step{i:02d}_before.png").write_bytes(before)

        gd = None
        pt = None
        if verb in CLICK_VERBS:
            gd = ground(args.ug_url, before, rest)
            pt = (gd["x"], gd["y"])
        cmd, coords = build_action(verb, rest, pt)
        print(f"[replay] step {i}: `{verb}` {rest!r} -> coords={coords} cmd={cmd!r}", flush=True)
        if cmd is None:
            print(f"[replay]   (skipped unknown verb {verb})", flush=True)
            continue

        obs, _, _, _ = env.step(cmd, pause=args.step_pause)
        (shots / f"step{i:02d}_after.png").write_bytes(obs["screenshot"])
        trace.append({
            "task_id": task["id"], "seed": 0, "step": i,
            "human_step": step, "verb": verb, "target": rest,
            "action": {"type": verb.lower(), "command": cmd},
            "coords": list(coords) if coords else None,
            "ground_raw": gd.get("raw") if gd else None,
            "cot": step,
            "screenshot_path": f"screenshots/step{i:02d}_after.png",
        })

    print("[replay] evaluating ...", flush=True)
    try:
        score = float(env.evaluate())
    except Exception as e:  # noqa: BLE001
        print(f"[replay] evaluate() raised: {e!r}", flush=True)
        score = -1.0
    success = score >= 0.999
    (shots / "final.png").write_bytes(env.controller.get_screenshot())

    (out / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in trace) + "\n")
    (out / "manifest.json").write_text(json.dumps({
        "task_id": task["id"], "seed": 0, "model_id": args.model_id,
        "success": success, "score": score, "total_steps": len(trace),
        "instruction": task["instruction"], "guided_by": "osworld-human",
    }, indent=2))
    print(f"[replay] RESULT: score={score} success={success} steps={len(trace)}", flush=True)
    try:
        env.close()
    except Exception:
        pass
    return 0 if success else 3


if __name__ == "__main__":
    raise SystemExit(main())
