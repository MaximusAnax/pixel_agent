"""Load OSWorld-Human reference trajectories from the vendored cache."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cua_failure_analysis.osworld.metadata import (
  OsworldSources,
  load_sources,
  resolve_pin_dir,
  task_lookup,
)


@dataclass
class HumanReference:
  task_id: str
  domain: str
  single_action: list[str] = field(default_factory=list)
  grouped_action: list[list[str]] = field(default_factory=list)
  human_json_path: str = ""
  raw: dict[str, Any] = field(default_factory=dict)


def load_human_reference(
  task_id: str,
  domain: str | None = None,
  *,
  pin_dir: Path | None = None,
  sources: OsworldSources | None = None,
) -> HumanReference:
  src = sources or load_sources()
  root = pin_dir or src.pin_dir
  if domain is None:
    # Reuse task_lookup domain resolution via tasks tree / manifest.
    task = task_lookup(task_id, pin_dir=root, sources=src)
    domain = str(task["_domain"])
  path = root / "human" / domain / f"{task_id}.json"
  if not path.exists():
    raise FileNotFoundError(f"Missing vendored OSWorld-Human JSON: {path}")
  data = json.loads(path.read_text(encoding="utf-8"))
  hgt = data.get("human-ground-truth") or {}
  single = list(hgt.get("single-action") or [])
  grouped_raw = hgt.get("grouped-action") or []
  grouped: list[list[str]] = []
  for group in grouped_raw:
    if isinstance(group, list):
      grouped.append([str(x) for x in group])
    elif isinstance(group, str):
      grouped.append([group])
  return HumanReference(
    task_id=task_id,
    domain=domain,
    single_action=[str(x) for x in single],
    grouped_action=grouped,
    human_json_path=str(path),
    raw=data,
  )
