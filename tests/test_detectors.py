"""Tests for Tier-1 detectors."""

from cua_failure_analysis.detectors.tier1 import (
  detect_action_looping,
  detect_click_region_or_location,
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
