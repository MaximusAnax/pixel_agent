"""Tests for OSWorld-Human action parser."""

from cua_failure_analysis.oracle.action_parser import ActionTier, parse_human_action


def test_hotkey_deterministic():
  a = parse_human_action("`HOTKEY` Ctrl+Shift+T")
  assert a.kind == "HOTKEY"
  assert a.tier == ActionTier.DETERMINISTIC


def test_click_nl_grounded():
  a = parse_human_action("`CLICK` pivot table icon")
  assert a.kind == "CLICK"
  assert a.tier == ActionTier.GROUNDED


def test_click_cell_semi():
  a = parse_human_action("`CLICK` cell G1")
  assert a.tier == ActionTier.SEMI


def test_typing_deterministic():
  a = parse_human_action("`TYPING` 'Revenue'")
  assert a.tier == ActionTier.DETERMINISTIC
