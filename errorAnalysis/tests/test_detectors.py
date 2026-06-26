"""Tests for Tier-1 detectors."""

from cua_failure_analysis.detectors.tier1 import (
  detect_action_looping,
  detect_click_region_or_location,
  detect_long_horizon_weak,
  run_tier1_at_step,
)
from cua_failure_analysis.taxonomy import FailureLeaf
from cua_failure_analysis.trace.schema import A11yElement, TraceStep


def _step(step: int, cot: str, coords: list[float], state_hash: str = "s1") -> TraceStep:
  return TraceStep(
    task_id="t1",
    seed=0,
    step=step,
    cot=cot,
    coords=coords,
    state_hash=state_hash,
    a11y_snippet=[
      A11yElement(role="button", name="Done", bbox=[80, 40, 120, 70], interactive=True)
    ],
  )


def test_action_looping():
  steps = [_step(i, "click Done", [105, 52]) for i in range(3)]
  result = detect_action_looping(steps)
  assert result is not None
  assert result.leaf == FailureLeaf.ACTION_LOOPING


def test_click_region_error():
  step = _step(1, "Click the Done button", [125, 55])
  result = detect_click_region_or_location(step)
  assert result is not None
  assert result.leaf == FailureLeaf.CLICK_REGION_ERROR


def test_location_hallucination():
  step = _step(1, "Click the Done button", [400, 300])
  result = detect_click_region_or_location(step)
  assert result is not None
  assert result.leaf == FailureLeaf.LOCATION_HALLUCINATION


def _late_step_no_strong_signal(idx: int, total: int) -> list[TraceStep]:
  """Late failure with no looping/spatial/click match: should defer to judge."""
  steps = []
  for i in range(total):
    steps.append(
      TraceStep(
        task_id="t1",
        seed=0,
        step=i,
        cot="Reviewing the document before continuing.",
        coords=[10 * i + 1, 5 * i + 1],
        state_hash=f"s{i}",
        a11y_snippet=[],
      )
    )
  return steps


def test_long_horizon_weak_excluded_by_default():
  total = 15
  steps = _late_step_no_strong_signal(total - 1, total)
  result = run_tier1_at_step(steps, total - 1, instruction="Edit the report", total_steps=total)
  assert result is None


def test_long_horizon_weak_opt_in():
  total = 15
  steps = _late_step_no_strong_signal(total - 1, total)
  result = run_tier1_at_step(
    steps, total - 1, instruction="Edit the report", total_steps=total, include_weak=True
  )
  assert result is not None
  assert result.leaf == FailureLeaf.LONG_HORIZON_MEMORY


def test_long_horizon_detector_unit_unchanged():
  step = _late_step_no_strong_signal(14, 15)[-1]
  assert detect_long_horizon_weak(step, total_steps=15) is not None
  assert detect_long_horizon_weak(step, total_steps=5) is None
