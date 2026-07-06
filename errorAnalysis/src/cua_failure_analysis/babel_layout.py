"""Default Babel shared layout paths (mattlab pixel_agent project root)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BabelSharedLayout:
  group_root: str
  shared_repo: str
  error_analysis: str
  shared_output_root: str
  shared_venv: str
  packet_staging: str
  annotations_root: str


def default_mattlab_layout() -> BabelSharedLayout:
  group_root = "/data/group_data/mattlab/pixel_agent"
  return BabelSharedLayout(
    group_root=group_root,
    shared_repo=f"{group_root}/pixelAgent",
    error_analysis=f"{group_root}/pixelAgent/errorAnalysis",
    shared_output_root=f"{group_root}/outputs",
    shared_venv=f"{group_root}/.venv",
    packet_staging=f"{group_root}/review_packets",
    annotations_root=f"{group_root}/review_annotations",
  )


def layout_from_env(env: dict[str, str] | None = None) -> BabelSharedLayout:
  """Resolve layout from environment (or os.environ), with mattlab defaults."""
  e = env if env is not None else os.environ
  defaults = default_mattlab_layout()
  group_root = e.get("BABEL_GROUP_ROOT", defaults.group_root)
  shared_repo = e.get("BABEL_SHARED_REPO", f"{group_root}/pixelAgent")
  return BabelSharedLayout(
    group_root=group_root,
    shared_repo=shared_repo,
    error_analysis=e.get("BABEL_SHARED_ERROR_ANALYSIS", f"{shared_repo}/errorAnalysis"),
    shared_output_root=e.get("BABEL_SHARED_OUTPUT_ROOT", f"{group_root}/outputs"),
    shared_venv=e.get("BABEL_SHARED_VENV", f"{group_root}/.venv"),
    packet_staging=e.get("BABEL_PACKET_STAGING", f"{group_root}/review_packets"),
    annotations_root=e.get("BABEL_ANNOTATIONS_ROOT", f"{group_root}/review_annotations"),
  )
