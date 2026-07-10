"""Parse OSWorld-Human DSL action strings into typed records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ActionTier(str, Enum):
  DETERMINISTIC = "deterministic"
  SEMI = "semi"
  GROUNDED = "grounded"
  UNKNOWN = "unknown"


@dataclass(frozen=True)
class HumanAction:
  raw: str
  kind: str
  target: str
  tier: ActionTier


_PREFIX_RE = re.compile(r"^`([A-Z_]+)`\s*(.*)$", re.S)
_CELL_RE = re.compile(r"^cell\s+[A-Z]+\d+\s*$", re.I)
_SHEET_RE = re.compile(r"^sheet\s+['\"].+['\"]\s*$", re.I)

DETERMINISTIC_KINDS = frozenset(
  {"HOTKEY", "PRESS", "TYPING", "TYPE", "KEY_DOWN", "KEY_UP", "WAIT"}
)
GROUNDED_KINDS = frozenset(
  {"CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "MOVE_TO", "DRAG_TO", "SCROLL", "DRAG"}
)


def parse_human_action(raw: str) -> HumanAction:
  text = (raw or "").strip()
  match = _PREFIX_RE.match(text)
  if not match:
    return HumanAction(raw=text, kind="UNKNOWN", target=text, tier=ActionTier.UNKNOWN)
  kind = match.group(1).upper()
  target = match.group(2).strip()
  if kind in DETERMINISTIC_KINDS:
    tier = ActionTier.DETERMINISTIC
  elif kind in GROUNDED_KINDS:
    if kind == "CLICK" and (_CELL_RE.match(target) or _SHEET_RE.match(target)):
      tier = ActionTier.SEMI
    else:
      tier = ActionTier.GROUNDED
  else:
    tier = ActionTier.UNKNOWN
  return HumanAction(raw=text, kind=kind, target=target, tier=tier)


def classify_actions(actions: list[str]) -> list[HumanAction]:
  return [parse_human_action(a) for a in actions]
