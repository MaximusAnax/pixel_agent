"""Per-step trace schema and I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class A11yElement(BaseModel):
  role: str | None = None
  name: str | None = None
  bbox: list[float] | None = None  # [x1, y1, x2, y2]
  interactive: bool = False


class TraceStep(BaseModel):
  task_id: str
  seed: int
  step: int
  screenshot_path: str | None = None
  action: dict[str, Any] = Field(default_factory=dict)
  coords: list[float] | None = None
  cot: str = ""
  eval_signals: dict[str, Any] = Field(default_factory=dict)
  a11y_snippet: list[A11yElement] = Field(default_factory=list)
  task_tags: list[str] = Field(default_factory=list)
  instruction: str = ""
  eval_passed: bool | None = None
  state_hash: str | None = None


class RunManifest(BaseModel):
  model_config = {"protected_namespaces": ()}

  task_id: str
  seed: int
  model_id: str
  success: bool
  total_steps: int
  instruction: str = ""
  task_tags: list[str] = Field(default_factory=list)
  eval_message: str = ""


class AttributionResult(BaseModel):
  primary_mode: str
  secondary_modes: list[str] = Field(default_factory=list)
  propagated: bool = False
  meta_labels: list[str] = Field(default_factory=list)
  tier_used: str = "programmatic"
  evidence_cot_span: str = ""
  confidence: float = 0.0
  t_star: int = 0


class TraceLogger:
  """Append per-step JSONL traces for a run."""

  def __init__(self, output_dir: Path, task_id: str, seed: int) -> None:
    self.output_dir = output_dir
    self.task_id = task_id
    self.seed = seed
    self.output_dir.mkdir(parents=True, exist_ok=True)
    self.trace_path = self.output_dir / "trace.jsonl"
    self.screenshot_dir = self.output_dir / "screenshots"
    self.screenshot_dir.mkdir(exist_ok=True)

  def log_step(self, step: TraceStep) -> None:
    with self.trace_path.open("a", encoding="utf-8") as f:
      f.write(step.model_dump_json() + "\n")

  def write_manifest(self, manifest: RunManifest) -> None:
    (self.output_dir / "manifest.json").write_text(
      manifest.model_dump_json(indent=2), encoding="utf-8"
    )


def load_trace(trace_path: Path) -> list[TraceStep]:
  steps: list[TraceStep] = []
  with trace_path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        steps.append(TraceStep.model_validate_json(line))
  return steps


def load_runs(root: Path) -> list[Path]:
  """Find trace.jsonl files under traces/{model}/{task_id}/{seed}/."""
  return sorted(root.glob("**/trace.jsonl"))
