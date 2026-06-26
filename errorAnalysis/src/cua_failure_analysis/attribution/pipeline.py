"""Hybrid attribution: Tier-1 detectors then VLM judge fallback."""

from __future__ import annotations

from pathlib import Path

from typing import TYPE_CHECKING

from cua_failure_analysis.attribution.first_failure import find_first_failure_step
from cua_failure_analysis.detectors.tier1 import (
  detect_click_region_or_location,
  detect_spatial_reasoning,
  detect_text_matching_bias,
  run_tier1_at_step,
)
from cua_failure_analysis.judge.client import VLMJudge, VLMJudgeConfig
from cua_failure_analysis.judge.protocol import JudgeClient
from cua_failure_analysis.taxonomy import TASK_TAG_GATED, FailureLeaf
from cua_failure_analysis.trace.schema import AttributionResult, TraceStep, load_trace

if TYPE_CHECKING:
  pass

# Leaves that are commonly downstream consequences of an earlier root error.
CONSEQUENCE_LEAVES = frozenset(
  {FailureLeaf.ACTION_LOOPING.value, FailureLeaf.LONG_HORIZON_MEMORY.value}
)


def _gate_controlled_leaf(leaf: FailureLeaf, task_tags: list[str]) -> bool:
  required = TASK_TAG_GATED.get(leaf)
  if required is None:
    return True
  return required in task_tags


def _find_earlier_root_cause(
  steps: list[TraceStep], t_idx: int, instruction: str
) -> tuple[int, str] | None:
  """Scan steps before ``t_idx`` for an earlier grounding error (root cause)."""
  for idx in range(t_idx):
    step = steps[idx]
    for detector in (
      detect_click_region_or_location(step),
      detect_text_matching_bias(step, instruction),
    ):
      if detector and detector.leaf:
        return step.step, detector.leaf.value
    spatial = detect_spatial_reasoning(step, instruction)
    if spatial and spatial.leaf and "relational" in step.task_tags:
      return step.step, spatial.leaf.value
  return None


def _tag_propagation(
  result: AttributionResult, steps: list[TraceStep], t_idx: int, instruction: str
) -> AttributionResult:
  """Mark consequence labels as propagated when an earlier root cause exists."""
  if result.primary_mode not in CONSEQUENCE_LEAVES:
    return result
  earlier = _find_earlier_root_cause(steps, t_idx, instruction)
  if earlier is None:
    return result
  root_step, root_leaf = earlier
  result.propagated = True
  if "propagated_failure" not in result.meta_labels:
    result.meta_labels = [*result.meta_labels, "propagated_failure"]
  suffix = f" | propagated from {root_leaf} at step {root_step}"
  if suffix not in result.evidence_cot_span:
    result.evidence_cot_span = f"{result.evidence_cot_span}{suffix}"
  return result


def attribute_run(
  trace_path: Path,
  instruction: str = "",
  judge: JudgeClient | None = None,
) -> AttributionResult:
  steps = load_trace(trace_path)
  if not steps:
    raise ValueError(f"Empty trace: {trace_path}")

  t_idx = find_first_failure_step(steps)
  step = steps[t_idx]
  instruction = instruction or step.instruction or ""
  task_tags = step.task_tags or steps[0].task_tags

  tier1 = run_tier1_at_step(steps, t_idx, instruction, len(steps))
  if tier1 and tier1.leaf and _gate_controlled_leaf(tier1.leaf, task_tags):
    result = AttributionResult(
      primary_mode=tier1.leaf.value,
      secondary_modes=[],
      propagated=False,
      tier_used=tier1.tier,
      evidence_cot_span=tier1.evidence,
      confidence=tier1.confidence,
      t_star=step.step,
    )
    return _tag_propagation(result, steps, t_idx, instruction)

  if judge is not None:
    prev = steps[max(0, t_idx - 3) : t_idx]
    result = judge.classify(
      step=step,
      instruction=instruction,
      previous_steps=prev,
      eval_message=step.eval_signals.get("message", ""),
    )
    leaf = FailureLeaf(result.primary_mode) if result.primary_mode in FailureLeaf._value2member_map_ else None
    if leaf and not _gate_controlled_leaf(leaf, task_tags):
      result.primary_mode = "Unresolved (missing task tag for controlled leaf)"
      result.confidence = 0.0
    result.t_star = step.step
    result.tier_used = "judge"
    return _tag_propagation(result, steps, t_idx, instruction)

  return AttributionResult(
    primary_mode="Unresolved",
    tier_used="none",
    confidence=0.0,
    t_star=step.step,
    evidence_cot_span="No programmatic match; judge not configured",
  )


def attribute_directory(
  traces_root: Path,
  output_path: Path,
  judge_config: VLMJudgeConfig | None = None,
) -> list[AttributionResult]:
  judge = VLMJudge(judge_config) if judge_config else None
  results: list[AttributionResult] = []
  output_path.parent.mkdir(parents=True, exist_ok=True)

  import json

  with output_path.open("w", encoding="utf-8") as out:
    for trace_path in sorted(traces_root.glob("**/trace.jsonl")):
      manifest_path = trace_path.parent / "manifest.json"
      instruction = ""
      if manifest_path.exists():
        instruction = json.loads(manifest_path.read_text()).get("instruction", "")
      attr = attribute_run(trace_path, instruction=instruction, judge=judge)
      record = {
        "trace_path": str(trace_path),
        **attr.model_dump(),
      }
      out.write(json.dumps(record) + "\n")
      results.append(attr)
  return results
