#!/usr/bin/env python3
"""Oracle Agent: replay a human trajectory step-by-step, capturing state.

Design doc: docs/oracle_agent_design.md. Two modes:

- --dry-run (works anywhere, no OSWorld): parse + normalize the trajectory,
  print the per-step pyautogui action plan, and validate it end-to-end.
- real mode (requires OSWorld's DesktopEnv on the VM host): executes each
  action, captures a screenshot before each step, waits for screen stability
  between steps, verifies init, and writes trace.jsonl + manifest.json in the
  cua_failure_analysis schema (model_id="human-oracle").

The OSWorld-Human adapter (`normalize_actions`) accepts the loose dict shapes
seen in trajectory dumps; verify against the real dataset schema in stage O1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# --- Action normalization (pure, offline, unit-tested) ---


@dataclass
class OracleAction:
  kind: str  # click | double_click | right_click | move | drag | type | key | hotkey | scroll | wait | done
  x: float | None = None
  y: float | None = None
  x2: float | None = None
  y2: float | None = None
  text: str | None = None
  keys: list[str] = field(default_factory=list)
  amount: int = 0  # scroll clicks (+up/-down)
  raw: dict = field(default_factory=dict)

  def to_pyautogui(self) -> str:
    """Render to OSWorld's `pyautogui` code-string action space."""
    if self.kind == "click":
      return f"pyautogui.click(x={self.x}, y={self.y})"
    if self.kind == "double_click":
      return f"pyautogui.doubleClick(x={self.x}, y={self.y})"
    if self.kind == "right_click":
      return f"pyautogui.rightClick(x={self.x}, y={self.y})"
    if self.kind == "move":
      return f"pyautogui.moveTo(x={self.x}, y={self.y})"
    if self.kind == "drag":
      return (
        f"pyautogui.moveTo(x={self.x}, y={self.y}); "
        f"pyautogui.dragTo(x={self.x2}, y={self.y2}, duration=0.5)"
      )
    if self.kind == "type":
      return f"pyautogui.typewrite({self.text!r}, interval=0.02)"
    if self.kind == "key":
      return f"pyautogui.press({self.keys[0]!r})"
    if self.kind == "hotkey":
      args = ", ".join(repr(k) for k in self.keys)
      return f"pyautogui.hotkey({args})"
    if self.kind == "scroll":
      return f"pyautogui.scroll({self.amount})"
    if self.kind == "wait":
      return "WAIT"
    if self.kind == "done":
      return "DONE"
    raise ValueError(f"Unrenderable action kind: {self.kind}")


_KIND_ALIASES = {
  "click": "click",
  "left_click": "click",
  "leftclick": "click",
  "double_click": "double_click",
  "doubleclick": "double_click",
  "right_click": "right_click",
  "rightclick": "right_click",
  "context_click": "right_click",
  "move": "move",
  "move_to": "move",
  "hover": "move",
  "drag": "drag",
  "drag_to": "drag",
  "type": "type",
  "typing": "type",
  "type_text": "type",
  "input": "type",
  "press": "key",
  "key": "key",
  "keydown": "key",
  "hotkey": "hotkey",
  "shortcut": "hotkey",
  "scroll": "scroll",
  "scroll_up": "scroll",
  "scroll_down": "scroll",
  "wait": "wait",
  "done": "done",
  "finish": "done",
  "terminate": "done",
}


def _coords(step: dict) -> tuple[float | None, float | None]:
  if isinstance(step.get("coordinate"), (list, tuple)) and len(step["coordinate"]) >= 2:
    return float(step["coordinate"][0]), float(step["coordinate"][1])
  if isinstance(step.get("coords"), (list, tuple)) and len(step["coords"]) >= 2:
    return float(step["coords"][0]), float(step["coords"][1])
  if step.get("x") is not None and step.get("y") is not None:
    return float(step["x"]), float(step["y"])
  pos = step.get("position") or {}
  if isinstance(pos, dict) and pos.get("x") is not None:
    return float(pos["x"]), float(pos["y"])
  return None, None


def normalize_action(step: dict) -> OracleAction:
  """Map one loose trajectory step dict to a canonical OracleAction."""
  raw_kind = str(step.get("type") or step.get("action") or step.get("action_type") or "").strip().lower()
  kind = _KIND_ALIASES.get(raw_kind)
  if kind is None:
    raise ValueError(f"Unknown action type {raw_kind!r} in step: {json.dumps(step)[:200]}")

  x, y = _coords(step)
  action = OracleAction(kind=kind, x=x, y=y, raw=step)

  if kind in ("click", "double_click", "right_click", "move") and (x is None or y is None):
    raise ValueError(f"{kind} without coordinates: {json.dumps(step)[:200]}")
  if kind == "drag":
    end = step.get("end") or step.get("target") or {}
    ex, ey = _coords(end if isinstance(end, dict) else {})
    if ex is None and isinstance(step.get("coordinate2"), (list, tuple)):
      ex, ey = float(step["coordinate2"][0]), float(step["coordinate2"][1])
    if x is None or ex is None:
      raise ValueError(f"drag needs start+end coordinates: {json.dumps(step)[:200]}")
    action.x2, action.y2 = ex, ey
  if kind == "type":
    text = step.get("text") if step.get("text") is not None else step.get("content")
    if text is None:
      raise ValueError(f"type without text: {json.dumps(step)[:200]}")
    action.text = str(text)
  if kind in ("key", "hotkey"):
    keys = step.get("keys") or step.get("key") or step.get("combination") or []
    if isinstance(keys, str):
      keys = keys.replace("-", "+").split("+") if kind == "hotkey" else [keys]
    if not keys:
      raise ValueError(f"{kind} without keys: {json.dumps(step)[:200]}")
    action.keys = [str(k).strip().lower() for k in keys]
    if kind == "key" and len(action.keys) > 1:
      action.kind = "hotkey"
  if kind == "scroll":
    amount = step.get("amount") or step.get("clicks") or step.get("dy") or 0
    if raw_kind == "scroll_down" and amount == 0:
      amount = -3
    if raw_kind == "scroll_up" and amount == 0:
      amount = 3
    action.amount = int(amount)
  return action


def normalize_actions(trajectory: list[dict]) -> list[OracleAction]:
  return [normalize_action(s) for s in trajectory]


def load_trajectory(path: Path) -> tuple[list[dict], dict]:
  """Return (steps, meta). Accepts {steps|actions|trajectory: [...]} or a bare list."""
  data = json.loads(path.read_text(encoding="utf-8"))
  if isinstance(data, list):
    return data, {}
  for key in ("steps", "actions", "trajectory", "action_list"):
    if isinstance(data.get(key), list):
      meta = {k: v for k, v in data.items() if k != key}
      return data[key], meta
  raise ValueError(f"No step list found in {path} (keys: {sorted(data)[:10]})")


# --- Replay session (needs OSWorld's DesktopEnv; import deferred) ---


class ReplaySession:
  def __init__(self, env, out_dir: Path, task_id: str, instruction: str,
               poll_interval: float = 0.5, stabilize_timeout: float = 10.0) -> None:
    from cua_failure_analysis.trace.schema import TraceLogger  # noqa: PLC0415

    self.env = env
    self.out_dir = out_dir
    self.task_id = task_id
    self.instruction = instruction
    self.poll_interval = poll_interval
    self.stabilize_timeout = stabilize_timeout
    self.logger = TraceLogger(out_dir, task_id, seed=0)
    self.stability_log: list[dict] = []

  def _screenshot_bytes(self) -> bytes:
    obs = self.env._get_obs() if hasattr(self.env, "_get_obs") else self.env.render()
    return obs["screenshot"] if isinstance(obs, dict) else obs

  def wait_until_stable(self, step_n: int) -> float:
    """Poll until two consecutive frames hash identically (anti-racing)."""
    start = time.monotonic()
    prev = hashlib.sha1(self._screenshot_bytes()).hexdigest()
    while time.monotonic() - start < self.stabilize_timeout:
      time.sleep(self.poll_interval)
      cur = hashlib.sha1(self._screenshot_bytes()).hexdigest()
      if cur == prev:
        break
      prev = cur
    waited = time.monotonic() - start
    self.stability_log.append({"step": step_n, "waited_s": round(waited, 2)})
    return waited

  def verify_init(self) -> None:
    shot = self._screenshot_bytes()
    (self.out_dir / "init_screenshot.png").write_bytes(shot)
    if not shot:
      raise RuntimeError("init_error: empty screenshot after reset")

  def run(self, actions: list[OracleAction]) -> None:
    from cua_failure_analysis.trace.schema import TraceStep  # noqa: PLC0415

    for n, action in enumerate(actions, start=1):
      shot_path = self.out_dir / "screenshots" / f"step_{n:03d}.png"
      shot_path.parent.mkdir(parents=True, exist_ok=True)
      shot = self._screenshot_bytes()
      shot_path.write_bytes(shot)
      code = action.to_pyautogui()
      if code == "WAIT":
        time.sleep(max(self.poll_interval, 1.0))
      elif code != "DONE":
        self.env.step(code)
      waited = self.wait_until_stable(n)
      self.logger.log_step(
        TraceStep(
          task_id=self.task_id,
          seed=0,
          step=n,
          screenshot_path=str(shot_path),
          action={"type": action.kind, "pyautogui": code},
          coords=[action.x, action.y] if action.x is not None else None,
          cot=f"[human-oracle] replayed step {n}; stabilized after {waited:.1f}s",
          instruction=self.instruction,
          state_hash=hashlib.sha1(shot).hexdigest()[:12],
        )
      )
    (self.out_dir / "stability_log.json").write_text(
      json.dumps(self.stability_log, indent=2), encoding="utf-8"
    )


def main() -> None:
  p = argparse.ArgumentParser(description="Replay a human trajectory (Oracle Agent)")
  p.add_argument("--trajectory", type=Path, required=True)
  p.add_argument("--task-config", type=Path, default=None, help="OSWorld task json (real mode)")
  p.add_argument("--out", type=Path, default=None)
  p.add_argument("--dry-run", action="store_true")
  p.add_argument("--verify-init", action="store_true")
  p.add_argument("--poll-interval", type=float, default=0.5)
  p.add_argument("--stabilize-timeout", type=float, default=10.0)
  args = p.parse_args()

  steps, meta = load_trajectory(args.trajectory)
  actions = normalize_actions(steps)
  task_id = str(meta.get("task_id") or args.trajectory.stem)
  instruction = str(meta.get("instruction") or meta.get("task") or "")

  print(f"task_id={task_id} steps={len(actions)} instruction={instruction[:80]!r}")
  for n, action in enumerate(actions, start=1):
    print(f"  {n:03d}: {action.to_pyautogui()}")
  if args.dry_run:
    print("dry-run OK — trajectory parses and renders end-to-end.")
    return

  if args.out is None or args.task_config is None:
    raise SystemExit("real mode needs --out and --task-config")
  try:
    from desktop_env.desktop_env import DesktopEnv  # type: ignore  # noqa: PLC0415
  except ImportError as exc:  # pragma: no cover - requires OSWorld host
    raise SystemExit(
      "OSWorld's desktop_env is not installed here. Run on the OSWorld VM host "
      "(see docs/oracle_agent_design.md stage O1), or use --dry-run."
    ) from exc

  task_config = json.loads(args.task_config.read_text(encoding="utf-8"))
  env = DesktopEnv(action_space="pyautogui")
  env.reset(task_config=task_config)
  session = ReplaySession(env, args.out, task_id, instruction,
                          poll_interval=args.poll_interval,
                          stabilize_timeout=args.stabilize_timeout)
  if args.verify_init:
    session.verify_init()
  session.run(actions)

  score = env.evaluate()
  from cua_failure_analysis.trace.schema import RunManifest  # noqa: PLC0415

  session.logger.write_manifest(
    RunManifest(
      task_id=task_id, seed=0, model_id="human-oracle",
      success=bool(score and float(score) >= 1.0),
      total_steps=len(actions), instruction=instruction,
      eval_message=f"osworld_score={score}",
    )
  )
  if not score or float(score) < 1.0:
    (args.out / "incomplete_step_report.json").write_text(
      json.dumps(
        {
          "task_id": task_id,
          "osworld_score": score,
          "hypothesis": "human trajectory incomplete (e.g. missing Enter) or evaluator/init issue",
          "last_actions": [a.to_pyautogui() for a in actions[-3:]],
        },
        indent=2,
      ),
      encoding="utf-8",
    )
    print("WARNING: replayed human trajectory did NOT pass the evaluator — "
          "wrote incomplete_step_report.json")


if __name__ == "__main__":
  main()
