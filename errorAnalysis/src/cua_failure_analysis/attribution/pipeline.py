"""Hybrid attribution: Tier-1 detectors then VLM judge fallback."""

from __future__ import annotations

from pathlib import Path

from typing import TYPE_CHECKING

from cua_failure_analysis.attribution.first_failure import find_first_failure_step
from cua_failure_analysis.detectors.tier1 import run_tier1_at_step
from cua_failure_analysis.judge.client import VLMJudge, VLMJudgeConfig
from cua_failure_analysis.judge.protocol import JudgeClient
from cua_failure_analysis.taxonomy import TASK_TAG_GATED, FailureLeaf
from cua_failure_analysis.trace.schema import AttributionResult, TraceStep, load_trace

if TYPE_CHECKING:
  pass


def _gate_controlled_leaf(leaf: FailureLeaf, task_tags: list[str]) -> bool:
  required = TASK_TAG_GATED.get(leaf)
  if required is None:
    return True
  return required in task_tags


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
    return AttributionResult(
      primary_mode=tier1.leaf.value,
      secondary_modes=[],
      propagated=False,
      tier_used=tier1.tier,
      evidence_cot_span=tier1.evidence,
      confidence=tier1.confidence,
      t_star=step.step,
    )

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
    return result

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
