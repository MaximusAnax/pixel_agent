"""Tests for the offline half of the Oracle Agent (normalization + dry-run)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
  "oracle_replay", Path(__file__).resolve().parents[1] / "scripts" / "oracle_replay.py"
)
oracle_replay = importlib.util.module_from_spec(SPEC)
sys.modules["oracle_replay"] = oracle_replay  # dataclasses need a registered module
SPEC.loader.exec_module(oracle_replay)

normalize_action = oracle_replay.normalize_action
normalize_actions = oracle_replay.normalize_actions
load_trajectory = oracle_replay.load_trajectory


def test_click_variants():
  for payload in (
    {"type": "click", "coordinate": [100, 200]},
    {"action": "left_click", "x": 100, "y": 200},
    {"action_type": "CLICK", "position": {"x": 100, "y": 200}},
  ):
    action = normalize_action(payload)
    assert action.kind == "click"
    assert action.to_pyautogui() == "pyautogui.click(x=100.0, y=200.0)"


def test_type_and_keys():
  assert normalize_action({"type": "type", "text": "hello"}).to_pyautogui() == \
    "pyautogui.typewrite('hello', interval=0.02)"
  assert normalize_action({"type": "press", "key": "enter"}).to_pyautogui() == \
    "pyautogui.press('enter')"
  hot = normalize_action({"type": "hotkey", "combination": "ctrl+s"})
  assert hot.to_pyautogui() == "pyautogui.hotkey('ctrl', 's')"
  # multi-key press coerces to hotkey
  assert normalize_action({"type": "press", "keys": ["ctrl", "c"]}).kind == "hotkey"


def test_scroll_defaults():
  assert normalize_action({"type": "scroll_down"}).amount == -3
  assert normalize_action({"type": "scroll_up"}).amount == 3
  assert normalize_action({"type": "scroll", "amount": 7}).amount == 7


def test_drag_requires_endpoints():
  action = normalize_action(
    {"type": "drag", "coordinate": [1, 2], "coordinate2": [3, 4]}
  )
  assert "dragTo(x=3.0, y=4.0" in action.to_pyautogui()
  with pytest.raises(ValueError, match="drag"):
    normalize_action({"type": "drag", "coordinate": [1, 2]})


def test_unknown_and_missing_fields_fail_loudly():
  with pytest.raises(ValueError, match="Unknown action type"):
    normalize_action({"type": "teleport"})
  with pytest.raises(ValueError, match="without coordinates"):
    normalize_action({"type": "click"})
  with pytest.raises(ValueError, match="without text"):
    normalize_action({"type": "type"})


def test_load_trajectory_shapes(tmp_path):
  bare = tmp_path / "bare.json"
  bare.write_text(json.dumps([{"type": "click", "x": 1, "y": 2}]))
  steps, meta = load_trajectory(bare)
  assert len(steps) == 1 and meta == {}

  wrapped = tmp_path / "wrapped.json"
  wrapped.write_text(json.dumps(
    {"task_id": "t1", "instruction": "do it", "steps": [{"type": "done"}]}
  ))
  steps, meta = load_trajectory(wrapped)
  assert meta["task_id"] == "t1"
  assert normalize_actions(steps)[0].to_pyautogui() == "DONE"


def test_end_to_end_dry_plan(tmp_path):
  traj = tmp_path / "traj.json"
  traj.write_text(json.dumps(
    {
      "task_id": "demo",
      "instruction": "save the file",
      "steps": [
        {"type": "click", "coordinate": [220, 115]},
        {"type": "type", "text": "report.txt"},
        {"type": "hotkey", "combination": "ctrl+s"},
        {"type": "wait"},
        {"type": "done"},
      ],
    }
  ))
  steps, _ = load_trajectory(traj)
  plan = [a.to_pyautogui() for a in normalize_actions(steps)]
  assert plan == [
    "pyautogui.click(x=220.0, y=115.0)",
    "pyautogui.typewrite('report.txt', interval=0.02)",
    "pyautogui.hotkey('ctrl', 's')",
    "WAIT",
    "DONE",
  ]
