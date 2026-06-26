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
ZIP_ROOT_SKIP = frozenset({"args.json", "metadata.json", "manifest.json"})


def episode_key_from_member(member: str) -> str | None:
  """Return `{domain}/{uuid}` when member is under a task directory."""
  parts = [p for p in member.split("/") if p]
  if len(parts) < 2:
    return None
  domain, task_id = parts[0], parts[1]
  if domain.lower() in ZIP_ROOT_SKIP or task_id.lower() in ZIP_ROOT_SKIP:
    return None
  if not UUID_RE.match(task_id):
    return None
  return f"{domain}/{task_id}"


def group_opencua_episodes(zf: zipfile.ZipFile) -> list[EpisodeBundle]:
  """Group zip members by OSWorld task (`{domain}/{uuid}`), excluding zip-root config."""
  groups: dict[str, list[str]] = defaultdict(list)
  for info in zf.infolist():
    if info.is_dir():
      continue
    key = episode_key_from_member(info.filename)
    if key is None:
      continue
    groups[key].append(info.filename)

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
