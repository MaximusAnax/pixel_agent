"""Executors: run one candidate over the eval set, produce predictions.

DetectorExecutor is offline, deterministic, and free — the P0 loop.
JudgeExecutor calls a VLM endpoint and meters cost against a hard budget — P1.
Both return {case_id: frozenset(predicted modes)} for objective.score_predictions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from cua_failure_analysis.attribution.first_failure import find_first_failure_step
from cua_failure_analysis.detectors import tier1
from cua_failure_analysis.taxonomy import TASK_TAG_GATED, FailureLeaf
from cua_failure_analysis.trace.schema import TraceStep, load_trace

from auto_research.budget import CostMeter
from auto_research.candidates import Candidate
from auto_research.objective import EvalCase, EvalSet


def _gate_ok(leaf: FailureLeaf, task_tags: list[str]) -> bool:
  required = TASK_TAG_GATED.get(leaf)
  return required is None or required in task_tags


@dataclass
class DetectorExecutor:
  """Parametrized Tier-1 decision order (mirrors run_tier1_at_step, with knobs)."""

  name: str = "detector"

  def predict_case(self, candidate: Candidate, case: EvalCase) -> frozenset[str]:
    steps = load_trace(case.trace_path)
    if not steps:
      return frozenset()
    t_idx = find_first_failure_step(steps)
    step = steps[t_idx]
    prefix = steps[: t_idx + 1]
    instruction = case.instruction or step.instruction or ""
    task_tags = case.task_tags or step.task_tags or steps[0].task_tags
    params = candidate.detectors

    result = None
    for det in params.order:
      result = self._run_detector(det, params, step, prefix, instruction, len(steps))
      if result is not None and result.leaf is not None:
        if _gate_ok(result.leaf, task_tags):
          break
        result = None
    if result is None or result.leaf is None:
      return frozenset()
    return frozenset({result.leaf.value})

  @staticmethod
  def _run_detector(
    name: str,
    params,
    step: TraceStep,
    prefix: list[TraceStep],
    instruction: str,
    total_steps: int,
  ):
    if name == "action_looping":
      return tier1.detect_action_looping(prefix, min_repeat=params.min_repeat)
    if name == "spatial_reasoning":
      result = tier1.detect_spatial_reasoning(step, instruction)
      # keep parity with run_tier1_at_step: only trust when tag-confirmed
      if result and "relational" not in step.task_tags:
        return None
      return result
    if name == "click_region_or_location":
      return tier1.detect_click_region_or_location(
        step,
        near_margin_ratio=params.near_margin_ratio,
        far_threshold_px=params.far_threshold_px,
      )
    if name == "text_matching_bias":
      return tier1.detect_text_matching_bias(step, instruction)
    if name == "long_horizon":
      if total_steps < params.long_horizon_min_total_steps:
        return None
      if step.step >= total_steps * params.long_horizon_threshold_ratio:
        return tier1.DetectorResult(
          leaf=FailureLeaf.LONG_HORIZON_MEMORY,
          confidence=0.5,
          evidence=f"Failure at late step {step.step}/{total_steps}",
        )
      return None
    raise ValueError(f"Unknown detector: {name}")

  def run(self, candidate: Candidate, eval_set: EvalSet) -> dict[str, frozenset[str]]:
    return {c.case_id: self.predict_case(candidate, c) for c in eval_set.cases}


@dataclass
class JudgeExecutor:
  """VLM judge over an OpenAI-compatible endpoint, hard-capped by CostMeter.

  ``client`` is any object exposing chat.completions.create(...) — the real
  OpenAI client pointed at vLLM/an API, or a fake in tests. No client means
  construction-time failure, never silent no-ops.
  """

  client: object
  meter: CostMeter
  erroranalysis_root: object = None  # Path to errorAnalysis/ for anchors
  name: str = "judge"

  def run(self, candidate: Candidate, eval_set: EvalSet) -> dict[str, frozenset[str]]:
    from pathlib import Path

    from cua_failure_analysis.judge import prompts as judge_prompts

    jp = candidate.judge
    anchors = None
    if jp.anchors_path:
      base = Path(self.erroranalysis_root) if self.erroranalysis_root else Path(".")
      anchors = base / jp.anchors_path

    if jp.protocol == "v2_multilabel":
      system_prompt = judge_prompts.build_system_prompt_v2(
        anchors, decision_order=jp.decision_order, extra_rules=jp.extra_rules
      )
    else:
      system_prompt = judge_prompts.build_system_prompt(anchors)

    predictions: dict[str, frozenset[str]] = {}
    for case in eval_set.cases:
      steps = load_trace(case.trace_path)
      if not steps:
        predictions[case.case_id] = frozenset()
        continue
      t_idx = find_first_failure_step(steps)
      step = steps[t_idx]
      prev = steps[max(0, t_idx - jp.prev_steps_k) : t_idx]
      prev_summary = "\n".join(
        f"step {s.step}: {s.action.get('type', 'action')} cot={s.cot[:120]}..." for s in prev
      )
      if jp.protocol == "v2_multilabel":
        user_text = judge_prompts.build_user_prompt_v2(
          instruction=case.instruction or step.instruction,
          cot=step.cot,
          action_json=json.dumps(step.action),
          previous_summary=prev_summary,
          reference_summary=(case.reference_summary or None)
          if jp.include_reference_trajectory
          else None,
          osworld_score=case.osworld_score if jp.include_osworld_score else None,
          eval_output=(case.eval_output or None) if jp.include_eval_output else None,
        )
      else:
        user_text = judge_prompts.build_user_prompt(
          instruction=case.instruction or step.instruction,
          cot=step.cot,
          action_json=json.dumps(step.action),
          eval_message=case.eval_output or step.eval_signals.get("message", ""),
          previous_summary=prev_summary or "(none)",
        )

      self.meter.charge_call(system_prompt, user_text, jp.expected_output_tokens,
                             images=1 if jp.include_screenshot and step.screenshot_path else 0)

      response = self.client.chat.completions.create(
        model=jp.model,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": [{"type": "text", "text": user_text}]},
        ],
        temperature=0.0,
        max_tokens=jp.max_tokens,
      )
      raw = response.choices[0].message.content or "{}"
      predictions[case.case_id] = self._parse_modes(raw)
    return predictions

  @staticmethod
  def _parse_modes(raw: str) -> frozenset[str]:
    raw = raw.strip()
    if raw.startswith("```"):
      raw = raw.split("```")[1]
      if raw.startswith("json"):
        raw = raw[4:]
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError:
      return frozenset()
    modes: list[str] = []
    if isinstance(parsed.get("modes"), list):
      modes = [str(m) for m in parsed["modes"]]
    else:
      if parsed.get("primary_mode"):
        modes.append(str(parsed["primary_mode"]))
      if isinstance(parsed.get("secondary_modes"), list):
        modes.extend(str(m) for m in parsed["secondary_modes"])
    valid = {leaf.value for leaf in FailureLeaf}
    return frozenset(m for m in modes if m in valid)
