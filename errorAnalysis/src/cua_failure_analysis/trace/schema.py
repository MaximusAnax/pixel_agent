"""Per-step trace schema and I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


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
  # OSWorld context (populated when vendored metadata is available)
  canonical_instruction: str = ""
  eval_bundle: str = ""
  human_reference_actions: list[str] = Field(default_factory=list)
  human_reference_grouped: list[list[str]] = Field(default_factory=list)
  osworld_task_path: str = ""
  domain: str = ""


class AttributionResult(BaseModel):
  """Judge/detector attribution for one failed run.

  All-applicable labeling policy (ratified 2026-08-10): ``modes_ordered`` lists
  **every** applicable leaf at ``t_star``, most-central-first. ``primary_mode``
  and ``secondary_modes`` are kept in sync for backward compatibility
  (``primary_mode == modes_ordered[0]``); old single-primary records load
  unchanged and gain a derived ``modes_ordered``.
  """

  primary_mode: str = "Unresolved"
  secondary_modes: list[str] = Field(default_factory=list)
  modes_ordered: list[str] = Field(default_factory=list)
  propagated: bool = False
  meta_labels: list[str] = Field(default_factory=list)
  tier_used: str = "programmatic"
  evidence_cot_span: str = ""
  confidence: float = 0.0
  t_star: int = 0

  @model_validator(mode="after")
  def _sync_mode_fields(self) -> "AttributionResult":
    if self.modes_ordered:
      deduped: list[str] = []
      for m in self.modes_ordered:
        if m and m not in deduped:
          deduped.append(m)
      self.modes_ordered = deduped
      if not self.primary_mode or self.primary_mode == "Unresolved":
        self.primary_mode = deduped[0]
      if not self.secondary_modes:
        self.secondary_modes = [m for m in deduped if m != self.primary_mode]
    elif self.primary_mode and self.primary_mode != "Unresolved":
      self.modes_ordered = [
        self.primary_mode,
        *[m for m in self.secondary_modes if m and m != self.primary_mode],
      ]
    return self


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
