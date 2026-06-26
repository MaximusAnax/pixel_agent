"""Anthropic Claude API judge for failure attribution."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

from anthropic import Anthropic

from cua_failure_analysis.judge.client import VLMJudge
from cua_failure_analysis.judge.prompts import build_system_prompt, build_user_prompt
from cua_failure_analysis.judge.usage import JudgeUsage
from cua_failure_analysis.trace.schema import AttributionResult, TraceStep


@dataclass
class AnthropicJudgeConfig:
  api_key: str
  model: str = "claude-sonnet-4-6"
  anchors_path: Path | None = None
  max_tokens: int = 512


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
  ) -> AttributionResult:
    prev_summary = "\n".join(
      f"step {s.step}: {s.action.get('type', 'action')} cot={s.cot[:120]}..."
      for s in previous_steps
    )
    user_text = build_user_prompt(
      instruction=instruction,
      cot=step.cot,
      action_json=json.dumps(step.action),
      eval_message=eval_message,
      previous_summary=prev_summary or "(none)",
    )

    content: list[dict] = []
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
    return AttributionResult(
      primary_mode=parsed.get("primary_mode", "Unresolved"),
      secondary_modes=parsed.get("secondary_modes", []),
      propagated=bool(parsed.get("propagated", False)),
      meta_labels=parsed.get("meta_labels", []),
      tier_used="judge",
      evidence_cot_span=parsed.get("evidence_cot_span", ""),
      confidence=float(parsed.get("confidence", 0.0)),
      t_star=step.step,
    )
