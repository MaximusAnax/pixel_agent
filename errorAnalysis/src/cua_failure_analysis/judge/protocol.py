"""Shared judge interface for attribution pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from cua_failure_analysis.trace.schema import AttributionResult, TraceStep


class JudgeClient(Protocol):
  def classify(
    self,
    step: TraceStep,
    instruction: str,
    previous_steps: list[TraceStep],
    eval_message: str = "",
    *,
    canonical_instruction: str = "",
    eval_bundle: str = "",
    human_reference_steps: list[dict[str, Any]] | None = None,
  ) -> AttributionResult: ...
