"""Anthropic Claude API judge for failure attribution."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from cua_failure_analysis.judge.client import VLMJudge, attribution_from_parsed
from cua_failure_analysis.judge.prompts import (
  build_system_prompt,
  build_user_prompt,
  format_human_reference_text,
)
from cua_failure_analysis.judge.usage import JudgeUsage
from cua_failure_analysis.trace.schema import AttributionResult, TraceStep


@dataclass
class AnthropicJudgeConfig:
  api_key: str
  model: str = "claude-sonnet-4-6"
  anchors_path: Path | None = None
  # Headroom so the JSON object always completes after any brief reasoning.
  max_tokens: int = 1024


@dataclass
class AnthropicJudge:
  config: AnthropicJudgeConfig
  system_prompt: str = field(init=False)
  last_usage: JudgeUsage | None = field(default=None, init=False)

  def __post_init__(self) -> None:
    anchors = self.config.anchors_path
    if anchors is None:
      default = Path(__file__).resolve().parents[3] / "config" / "judge_anchors.yaml"
      anchors = default if default.exists() else None
    self.system_prompt = build_system_prompt(anchors)

  def _client(self) -> Anthropic:
    return Anthropic(api_key=self.config.api_key)

  @staticmethod
  def _read_image_b64(path: str | None) -> tuple[str, str] | None:
    if not path or not Path(path).exists():
      return None
    data = Path(path).read_bytes()
    media_type = "image/png"
    if path.lower().endswith((".jpg", ".jpeg")):
      media_type = "image/jpeg"
    elif path.lower().endswith(".webp"):
      media_type = "image/webp"
    return base64.standard_b64encode(data).decode("ascii"), media_type

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
  ) -> AttributionResult:
    prev_summary = "\n".join(
      f"step {s.step}: {s.action.get('type', 'action')} cot={s.cot[:120]}..."
      for s in previous_steps
    )
    action = step.action or {}
    user_text = build_user_prompt(
      instruction=instruction,
      cot=step.cot,
      action_json=json.dumps(action),
      eval_message=eval_message,
      previous_summary=prev_summary or "(none)",
      canonical_instruction=canonical_instruction or instruction,
      eval_bundle=eval_bundle or eval_message,
      executed_action=str(action.get("raw_code") or ""),
      model_code=str(action.get("model_code") or ""),
      stated_intent=str(action.get("stated_intent") or action.get("action_section") or ""),
      grounding_mismatch=action.get("grounding_mismatch"),
      human_reference_text=format_human_reference_text(human_reference_steps),
    )

    content: list[dict] = []
    # Full human sequence images first (non-binding reference), then model obs at t*.
    for row in human_reference_steps or []:
      image = self._read_image_b64(row.get("image_path"))
      if not image:
        continue
      b64, media_type = image
      content.append(
        {
          "type": "image",
          "source": {"type": "base64", "media_type": media_type, "data": b64},
        }
      )
    image = self._read_image_b64(step.screenshot_path)
    if image:
      b64, media_type = image
      content.append(
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": media_type,
            "data": b64,
          },
        }
      )
    content.append({"type": "text", "text": user_text})

    response = self._client().messages.create(
      model=self.config.model,
      max_tokens=self.config.max_tokens,
      system=self.system_prompt,
      messages=[{"role": "user", "content": content}],
      temperature=0.0,
    )

    input_tokens = getattr(response.usage, "input_tokens", 0) or 0
    output_tokens = getattr(response.usage, "output_tokens", 0) or 0
    self.last_usage = JudgeUsage(
      input_tokens=input_tokens,
      output_tokens=output_tokens,
      model=self.config.model,
    )

    raw = ""
    for block in response.content:
      if getattr(block, "type", None) == "text":
        raw += block.text
    parsed = VLMJudge._parse_json(raw)
    return attribution_from_parsed(parsed, t_star=step.step)
