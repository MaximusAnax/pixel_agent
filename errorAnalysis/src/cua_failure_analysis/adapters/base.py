"""Adapter protocols and shared types for HF trajectory packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cua_failure_analysis.trace.schema import RunManifest, TraceStep


@dataclass
class EpisodeBundle:
  """One OSWorld task run inside an HF zip."""

  episode_id: str
  task_id: str
  domain: str
  members: list[str] = field(default_factory=list)

  @property
  def json_members(self) -> list[str]:
    return [m for m in self.members if m.lower().endswith((".json", ".jsonl"))]

  @property
  def text_members(self) -> list[str]:
    return [m for m in self.members if m.lower().endswith((".txt", ".md", ".log"))]

  @property
  def image_members(self) -> list[str]:
    return [m for m in self.members if m.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

  @property
  def result_members(self) -> list[str]:
    import re

    return [
      m
      for m in self.json_members + self.text_members
      if re.search(r"(result|eval|score|traj|trace|step|history|log)", Path(m).name, re.I)
    ]


@dataclass
class AdapterResult:
  manifest: RunManifest
  steps: list[TraceStep]


class TrajectoryAdapter(Protocol):
  def normalize_episode(
    self,
    bundle: EpisodeBundle,
    extracted_paths: list[Path],
    *,
    model_id: str,
    package: str,
  ) -> AdapterResult: ...
