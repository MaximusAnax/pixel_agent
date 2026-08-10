"""Hybrid attribution: Tier-1 detectors then VLM judge fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def _load_manifest(trace_path: Path) -> dict[str, Any]:
  manifest_path = trace_path.parent / "manifest.json"
  if not manifest_path.exists():
    return {}
  try:
    return json.loads(manifest_path.read_text(encoding="utf-8"))
  except json.JSONDecodeError:
    return {}


def resolve_oracle_dir(
  oracle_root: Path | None,
  domain: str,
  task_id: str,
) -> Path | None:
  """Locate partner oracle artifacts under ``<root>/<domain>/<task_id>`` or flat ``<root>/<task_id>``."""
  if oracle_root is None:
    return None
  root = Path(oracle_root)
  nested = root / domain / task_id
  if (nested / "human_traj.json").exists():
    return nested
  flat = root / task_id
  if (flat / "human_traj.json").exists():
    return flat
  return None


def load_human_reference_steps(
  *,
  oracle_dir: Path | None = None,
  human_traj_path: Path | None = None,
) -> tuple[list[dict[str, Any]], str]:
  """Load partner Human Agent artifacts for UI / multimodal judge context.

  Returns (steps, oracle_status) where each step is
  ``{action_text, image_path}`` and status is ready|partial|pending|failed|"".
  """
  traj_path = human_traj_path
  if traj_path is None and oracle_dir is not None:
    traj_path = oracle_dir / "human_traj.json"
  if traj_path is None or not traj_path.exists():
    return [], "pending"

  try:
    data = json.loads(traj_path.read_text(encoding="utf-8"))
  except json.JSONDecodeError:
    return [], "failed"

  status = str(data.get("oracle_status") or "ready")
  steps_out: list[dict[str, Any]] = []
  raw_steps = data.get("steps") or data.get("human_steps") or []
  base = traj_path.parent
  for row in raw_steps:
    if not isinstance(row, dict):
      continue
    action_text = str(row.get("action_text") or row.get("action") or "")
    image_name = row.get("observation_screenshot") or row.get("image_path") or ""
    image_path = ""
    if image_name:
      candidate = Path(str(image_name))
      if not candidate.is_absolute():
        candidate = base / candidate
      image_path = str(candidate) if candidate.exists() else ""
    steps_out.append({"action_text": action_text, "image_path": image_path or None})
  if not steps_out and status == "ready":
    status = "partial"
  return steps_out, status


def _grounding_mismatch_shortcut(step: TraceStep) -> AttributionResult | None:
  """Optional Tier-1 fast-path when proposed vs executed coords diverge."""
  action = step.action or {}
  if not action.get("grounding_mismatch"):
    return None
  if str(action.get("type") or "") != "click":
    return None
  return AttributionResult(
    primary_mode=FailureLeaf.CLICK_REGION_ERROR.value,
    secondary_modes=[],
    propagated=False,
    meta_labels=["grounding_mismatch_precheck"],
    tier_used="programmatic",
    evidence_cot_span=(
      "Programmatic grounding mismatch: model_code coords diverge from executed "
      f"trajectory. model_code={action.get('model_code')!r} "
      f"raw_code={action.get('raw_code')!r}"
    ),
    confidence=0.75,
    t_star=step.step,
  )


def attribute_run(
  trace_path: Path,
  instruction: str = "",
  judge: JudgeClient | None = None,
  *,
  oracle_dir: Path | None = None,
  human_traj_path: Path | None = None,
  require_oracle_for_judge: bool = False,
) -> AttributionResult:
  steps = load_trace(trace_path)
  if not steps:
    raise ValueError(f"Empty trace: {trace_path}")

  manifest = _load_manifest(trace_path)
  t_idx = find_first_failure_step(steps)
  step = steps[t_idx]
  instruction = (
    instruction
    or manifest.get("canonical_instruction")
    or manifest.get("instruction")
    or step.instruction
    or ""
  )
  task_tags = step.task_tags or steps[0].task_tags

  # Optional grounding mismatch shortcut before full Tier-1 / judge.
  shortcut = _grounding_mismatch_shortcut(step)
  if shortcut is not None:
    return _tag_propagation(shortcut, steps, t_idx, instruction)

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

  human_steps, oracle_status = load_human_reference_steps(
    oracle_dir=oracle_dir,
    human_traj_path=human_traj_path,
  )
  if require_oracle_for_judge and oracle_status not in {"ready", "partial"}:
    return AttributionResult(
      primary_mode="Unresolved",
      tier_used="none",
      confidence=0.0,
      t_star=step.step,
      evidence_cot_span=(
        f"Judge gated: oracle_status={oracle_status or 'missing'} "
        "(need ready|partial for osworld_v1 multimodal rejudge)"
      ),
      meta_labels=["oracle_gate"],
    )

  if judge is not None:
    prev = steps[max(0, t_idx - 3) : t_idx]
    eval_bundle = str(manifest.get("eval_bundle") or "")
    eval_message = (
      eval_bundle
      or step.eval_signals.get("message", "")
      or str(manifest.get("eval_message") or "")
    )
    # Prefer text human actions from manifest when oracle images absent.
    if not human_steps and manifest.get("human_reference_actions"):
      human_steps = [
        {"action_text": str(a), "image_path": None}
        for a in manifest.get("human_reference_actions") or []
      ]
    result = judge.classify(
      step=step,
      instruction=instruction,
      previous_steps=prev,
      eval_message=eval_message,
      canonical_instruction=str(manifest.get("canonical_instruction") or instruction),
      eval_bundle=eval_bundle or eval_message,
      human_reference_steps=human_steps or None,
    )
    leaf = (
      FailureLeaf(result.primary_mode)
      if result.primary_mode in FailureLeaf._value2member_map_
      else None
    )
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

  with output_path.open("w", encoding="utf-8") as out:
    for trace_path in sorted(traces_root.glob("**/trace.jsonl")):
      manifest = _load_manifest(trace_path)
      instruction = str(
        manifest.get("canonical_instruction") or manifest.get("instruction") or ""
      )
      attr = attribute_run(trace_path, instruction=instruction, judge=judge)
      record = {
        "trace_path": str(trace_path),
        **attr.model_dump(),
      }
      out.write(json.dumps(record) + "\n")
      results.append(attr)
  return results
