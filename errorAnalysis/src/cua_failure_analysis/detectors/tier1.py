"""Tier-1 programmatic failure detectors."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from cua_failure_analysis.taxonomy import FailureLeaf
from cua_failure_analysis.trace.schema import A11yElement, TraceStep


RELATIONAL_TERMS = re.compile(
  r"\b(left|right|above|below|top|bottom|beside|next to)\b", re.I
)


@dataclass
class DetectorResult:
  leaf: FailureLeaf | None
  confidence: float
  evidence: str
  tier: str = "programmatic"


def _action_key(step: TraceStep) -> str:
  action = step.action
  return json_dumps_stable(
    {
      "type": action.get("type") or action.get("action_type"),
      "coords": step.coords,
      "text": action.get("text") or action.get("content"),
    }
  )


def json_dumps_stable(obj: dict) -> str:
  import json

  return json.dumps(obj, sort_keys=True, default=str)


def detect_action_looping(
  steps: list[TraceStep], min_repeat: int = 3
) -> DetectorResult | None:
  if len(steps) < min_repeat:
    return None
  window = steps[-min_repeat:]
  keys = [_action_key(s) for s in window]
  state_unchanged = all(
    s.state_hash == window[0].state_hash and window[0].state_hash
    for s in window
  ) or all(s.eval_passed is not True for s in window)
  if len(set(keys)) == 1 and state_unchanged:
    return DetectorResult(
      leaf=FailureLeaf.ACTION_LOOPING,
      confidence=0.9,
      evidence=f"Repeated identical action {min_repeat}+ times at steps "
      f"{window[0].step}-{window[-1].step}",
    )
  return None


def _bbox_center(bbox: list[float]) -> tuple[float, float]:
  x1, y1, x2, y2 = bbox
  return (x1 + x2) / 2, (y1 + y2) / 2


def _point_in_bbox(x: float, y: float, bbox: list[float], margin: float = 0) -> bool:
  x1, y1, x2, y2 = bbox
  return x1 - margin <= x <= x2 + margin and y1 - margin <= y <= y2 + margin


def _distance(x: float, y: float, bbox: list[float]) -> float:
  x1, y1, x2, y2 = bbox
  cx = max(x1, min(x, x2))
  cy = max(y1, min(y, y2))
  return math.hypot(x - cx, y - cy)


def _cot_mentions_element(cot: str, element: A11yElement) -> bool:
  if not cot or not element.name:
    return False
  return element.name.lower() in cot.lower()


def find_cot_matched_elements(cot: str, elements: list[A11yElement]) -> list[A11yElement]:
  return [e for e in elements if e.name and e.name.lower() in cot.lower()]


def detect_click_region_or_location(
  step: TraceStep,
  near_margin_ratio: float = 1.5,
  far_threshold_px: float = 80.0,
) -> DetectorResult | None:
  if not step.coords or len(step.coords) < 2:
    return None
  x, y = float(step.coords[0]), float(step.coords[1])
  matched = find_cot_matched_elements(step.cot, step.a11y_snippet)
  if not matched:
    return None

  target = matched[0]
  if not target.bbox or len(target.bbox) < 4:
    return None

  x1, y1, x2, y2 = target.bbox
  w, h = x2 - x1, y2 - y1
  margin = max(w, h) * near_margin_ratio * 0.25

  if _point_in_bbox(x, y, target.bbox):
    return None

  dist = _distance(x, y, target.bbox)
  if dist <= margin:
    return DetectorResult(
      leaf=FailureLeaf.CLICK_REGION_ERROR,
      confidence=0.85,
      evidence=f"CoT names '{target.name}' but click ({x:.0f},{y:.0f}) outside bbox",
    )
  if dist > far_threshold_px:
    return DetectorResult(
      leaf=FailureLeaf.LOCATION_HALLUCINATION,
      confidence=0.8,
      evidence=f"CoT names '{target.name}' but click ({x:.0f},{y:.0f}) is {dist:.0f}px away",
    )
  return None


def detect_spatial_reasoning(
  step: TraceStep, instruction: str
) -> DetectorResult | None:
  if "relational" not in step.task_tags and not RELATIONAL_TERMS.search(instruction):
    return None
  matched = find_cot_matched_elements(step.cot, step.a11y_snippet)
  if not matched or not step.coords:
    return None
  return DetectorResult(
    leaf=FailureLeaf.SPATIAL_REASONING,
    confidence=0.6,
    evidence="Relational instruction with landmark in CoT; click may violate spatial relation",
    tier="programmatic",
  )


def detect_text_matching_bias(step: TraceStep, instruction: str) -> DetectorResult | None:
  if not step.coords or len(step.coords) < 2:
    return None
  x, y = float(step.coords[0]), float(step.coords[1])
  tokens = {t.lower() for t in re.findall(r"\w+", instruction) if len(t) > 2}
  for el in step.a11y_snippet:
    if not el.name or not el.bbox:
      continue
    name_lower = el.name.lower()
    if name_lower in tokens and not el.interactive:
      if _point_in_bbox(x, y, el.bbox, margin=5):
        return DetectorResult(
          leaf=FailureLeaf.TEXT_MATCHING_BIAS,
          confidence=0.75,
          evidence=f"Click on non-interactive label '{el.name}' matching instruction token",
          tier="a11y",
        )
  return None


def detect_long_horizon_weak(
  step: TraceStep, total_steps: int, threshold_ratio: float = 0.7
) -> DetectorResult | None:
  if total_steps < 10:
    return None
  if step.step >= total_steps * threshold_ratio:
    return DetectorResult(
      leaf=FailureLeaf.LONG_HORIZON_MEMORY,
      confidence=0.5,
      evidence=f"Failure at late step {step.step}/{total_steps}",
      tier="programmatic",
    )
  return None


def run_tier1_at_step(
  steps: list[TraceStep],
  t_star_idx: int,
  instruction: str,
  total_steps: int,
  include_weak: bool = False,
) -> DetectorResult | None:
  """Apply the global decision order at step index ``t_star_idx``.

  The weak Long-Horizon detector is a late-step heuristic, not a root-cause
  signal. Per failureStudyProtocol.md it stays diagnostic only: by default it is
  excluded so that late failures with no strong programmatic match fall through
  to the VLM judge instead of being auto-labeled Long-Horizon Memory Failure.
  Pass ``include_weak=True`` to opt back into the heuristic.
  """
  step = steps[t_star_idx]
  prefix = steps[: t_star_idx + 1]

  loop = detect_action_looping(prefix)
  if loop:
    return loop

  spatial = detect_spatial_reasoning(step, instruction)
  if spatial and "relational" in step.task_tags:
    return spatial

  click = detect_click_region_or_location(step)
  if click:
    return click

  text = detect_text_matching_bias(step, instruction)
  if text:
    return text

  if include_weak:
    late = detect_long_horizon_weak(step, total_steps)
    if late:
      return late

  return None
