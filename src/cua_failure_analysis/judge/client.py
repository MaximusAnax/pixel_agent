"""OpenAI-compatible VLM judge client."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from cua_failure_analysis.judge.prompts import build_system_prompt, build_user_prompt
from cua_failure_analysis.trace.schema import AttributionResult, TraceStep


@dataclass
class VLMJudgeConfig:
  base_url: str = "http://localhost:8000/v1"
  api_key: str = "EMPTY"
  model: str = "opencua-7b"
  anchors_path: Path | None = None


class VLMJudge:
  def __init__(self, config: VLMJudgeConfig | None = None) -> None:
    self.config = config or VLMJudgeConfig()
    anchors = self.config.anchors_path
    if anchors is None:
      default = Path(__file__).resolve().parents[3] / "config" / "judge_anchors.yaml"
      anchors = default if default.exists() else None
    self.system_prompt = build_system_prompt(anchors)

  def _client(self) -> OpenAI:
    return OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

  def _encode_image(self, path: str | None) -> str | None:
    if not path or not Path(path).exists():
      return None
    data = Path(path).read_bytes()
    b64 = base64.standard_b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"

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

    content: list[dict] = [{"type": "text", "text": user_text}]
    img = self._encode_image(step.screenshot_path)
    if img:
      content.append({"type": "image_url", "image_url": {"url": img}})

    response = self._client().chat.completions.create(
      model=self.config.model,
      messages=[
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": content},
      ],
      temperature=0.0,
      max_tokens=512,
    )
    raw = response.choices[0].message.content or "{}"
    parsed = self._parse_json(raw)
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

  @staticmethod
  def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
      raw = raw.split("```")[1]
      if raw.startswith("json"):
        raw = raw[4:]
    try:
      return json.loads(raw)
    except json.JSONDecodeError:
      return {"primary_mode": "Unresolved", "evidence_cot_span": raw[:200]}
