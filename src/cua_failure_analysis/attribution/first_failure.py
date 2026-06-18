"""First failure step detection."""

from __future__ import annotations

from cua_failure_analysis.trace.schema import TraceStep


def find_first_failure_step(steps: list[TraceStep]) -> int:
  """
  Return step index t* (0-based) for the earliest failure.

  Uses explicit eval_passed flags when present; otherwise last step.
  """
  for i, step in enumerate(steps):
    if step.eval_passed is False:
      return i
    signals = step.eval_signals or {}
    if signals.get("failed") or signals.get("evaluator_failed"):
      return i
  return max(0, len(steps) - 1)
