"""Package-specific trajectory adapters."""

from __future__ import annotations

from cua_failure_analysis.adapters.base import AdapterResult, EpisodeBundle, TrajectoryAdapter
from cua_failure_analysis.adapters.grouping import episode_key_from_member, group_opencua_episodes
from cua_failure_analysis.adapters.opencua_osworld import OpenCuaOsworldAdapter, normalize_opencua_episode

_OPENCUA_PREFIXES = (
  "opencua_agent-opencua_a3b",
  "opencua_agent-opencua_7b",
  "opencua_agent-opencua_32b",
)


def get_adapter(package: str) -> TrajectoryAdapter | None:
  lowered = package.lower()
  if any(lowered.startswith(prefix) for prefix in _OPENCUA_PREFIXES):
    return OpenCuaOsworldAdapter()
  return None


def uses_opencua_grouping(package: str) -> bool:
  return get_adapter(package) is not None


__all__ = [
  "AdapterResult",
  "EpisodeBundle",
  "OpenCuaOsworldAdapter",
  "TrajectoryAdapter",
  "episode_key_from_member",
  "get_adapter",
  "group_opencua_episodes",
  "normalize_opencua_episode",
  "uses_opencua_grouping",
]