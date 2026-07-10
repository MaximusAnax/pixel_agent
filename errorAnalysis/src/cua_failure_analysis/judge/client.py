"""OpenAI-compatible VLM judge client."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from cua_failure_analysis.judge.prompts import (
  build_system_prompt,
  build_user_prompt,
  format_human_reference_text,
)
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
    suffix = Path(path).suffix.lower()
    mime = "image/png"
    if suffix in {".jpg", ".jpeg"}:
      mime = "image/jpeg"
    elif suffix == ".webp":
      mime = "image/webp"
    return f"data:{mime};base64,{b64}"

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

    content: list[dict] = [{"type": "text", "text": user_text}]
    for row in human_reference_steps or []:
      img = self._encode_image(row.get("image_path"))
      if img:
        content.append({"type": "image_url", "image_url": {"url": img}})
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
    text = raw.strip()
    # Strip a leading ```json fence when the whole response is fenced.
    if text.startswith("```"):
      fenced = text.split("```")
      if len(fenced) >= 2:
        text = fenced[1]
        if text.startswith("json"):
          text = text[4:]
    text = text.strip()
    try:
      return json.loads(text)
    except json.JSONDecodeError:
      pass
    # The model often emits reasoning prose before/around the JSON object.
    # Recover the JSON by parsing the first balanced-brace object in the text.
    obj = _extract_json_object(raw)
    if obj is not None:
      return obj
    return {"primary_mode": "Unresolved", "evidence_cot_span": raw.strip()[:200]}


def _extract_json_object(text: str) -> dict | None:
  """Return the first balanced {...} object parseable as JSON, else None."""
  start = text.find("{")
  while start != -1:
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
      ch = text[i]
      if in_str:
        if escape:
          escape = False
        elif ch == "\\":
          escape = True
        elif ch == '"':
          in_str = False
        continue
      if ch == '"':
        in_str = True
      elif ch == "{":
        depth += 1
      elif ch == "}":
        depth -= 1
        if depth == 0:
          candidate = text[start : i + 1]
          try:
            return json.loads(candidate)
          except json.JSONDecodeError:
            break
    start = text.find("{", start + 1)
  return None
