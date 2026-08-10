"""Episode grouping heuristics for HF OSWorld trajectory zips."""

from __future__ import annotations

import re
import zipfile
from collections import defaultdict

from cua_failure_analysis.adapters.base import EpisodeBundle

UUID_RE = re.compile(
  r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
  re.I,
)
TURN_RE = re.compile(r"^turn_(\d+)$", re.I)
ZIP_ROOT_SKIP = frozenset({"args.json", "metadata.json", "manifest.json"})


def _parse_member(member: str) -> tuple[str | None, str, str] | None:
  """Return `(turn, domain, uuid)` for a task-scoped member, else None.

  Handles both the flat OpenCUA layout (`{domain}/{uuid}/...`, e.g. the A3B-15
  package) and the multi-attempt layout (`turn_N/{domain}/{uuid}/...`, e.g. the
  7B-15 package, which ships three attempts per task). The UUID is located
  positionally so a leading `turn_N/` prefix does not break grouping.
  """
  parts = [p for p in member.split("/") if p]
  uuid_idx = next((i for i, p in enumerate(parts) if UUID_RE.match(p)), None)
  if uuid_idx is None or uuid_idx == 0:
    return None
  task_id = parts[uuid_idx]
  domain = parts[uuid_idx - 1]
  if domain.lower() in ZIP_ROOT_SKIP:
    return None
  turn = parts[0] if (uuid_idx >= 2 and TURN_RE.match(parts[0])) else None
  return turn, domain, task_id


def episode_key_from_member(member: str) -> str | None:
  """Return `{domain}/{uuid}` when member is under a task directory."""
  parsed = _parse_member(member)
  if parsed is None:
    return None
  _turn, domain, task_id = parsed
  return f"{domain}/{task_id}"


def _turn_sort_key(turn: str) -> tuple[int, str]:
  m = TURN_RE.match(turn)
  return (int(m.group(1)), turn) if m else (1_000_000, turn)


def detect_turns(zf: zipfile.ZipFile) -> list[str]:
  """Return the sorted `turn_N` prefixes present in the zip (empty for flat layout)."""
  turns: set[str] = set()
  for info in zf.infolist():
    if info.is_dir():
      continue
    p = _parse_member(info.filename)
    if p is not None and p[0] is not None:
      turns.add(p[0])
  return sorted(turns, key=_turn_sort_key)


def group_opencua_episodes(
  zf: zipfile.ZipFile, *, select_turn: str | None = None
) -> list[EpisodeBundle]:
  """Group zip members by OSWorld task (`{domain}/{uuid}`), excluding zip-root config.

  When the package ships multiple attempts per task under `turn_N/` prefixes
  (e.g. OpenCUA-7B-15), only a single turn is grouped so the result stays
  matched (one attempt per task) with single-attempt packages like A3B-15.
  `select_turn` chooses which turn (e.g. ``"turn_1"``); when unset or absent,
  the lowest-numbered turn present is used.
  """
  parsed: list[tuple[str | None, str, str, str]] = []
  for info in zf.infolist():
    if info.is_dir():
      continue
    p = _parse_member(info.filename)
    if p is None:
      continue
    turn, domain, task_id = p
    parsed.append((turn, domain, task_id, info.filename))

  turns_present = sorted({t for (t, *_rest) in parsed if t is not None}, key=_turn_sort_key)
  chosen_turn: str | None = None
  if turns_present:
    chosen_turn = select_turn if select_turn in turns_present else turns_present[0]

  groups: dict[str, list[str]] = defaultdict(list)
  for turn, domain, task_id, filename in parsed:
    if chosen_turn is not None:
      # Multi-attempt package: keep only the selected turn.
      if turn != chosen_turn:
        continue
    elif turn is not None:
      # Flat package expected but a stray turn-prefixed member appeared; skip it.
      continue
    groups[f"{domain}/{task_id}"].append(filename)

  bundles: list[EpisodeBundle] = []
  for episode_id, members in sorted(groups.items()):
    domain, task_id = episode_id.split("/", 1)
    if not members:
      continue
    bundles.append(
      EpisodeBundle(
        episode_id=episode_id,
        task_id=task_id,
        domain=domain,
        members=sorted(members),
      )
    )
  return bundles
