"""Judge API usage and cost tracking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Rough Sonnet 4 list prices (USD per 1M tokens) — provisional for budgeting.
_SONNET4_INPUT_PER_M = 3.0
_SONNET4_OUTPUT_PER_M = 15.0


@dataclass
class JudgeUsage:
  input_tokens: int
  output_tokens: int
  model: str

  @property
  def estimated_cost_usd(self) -> float:
    return estimate_judge_cost_usd(self.model, self.input_tokens, self.output_tokens)


def estimate_judge_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
  """Rough USD estimate for budgeting (not billing-accurate)."""
  model_lower = model.lower()
  if "sonnet" in model_lower or "claude" in model_lower:
    in_rate, out_rate = _SONNET4_INPUT_PER_M, _SONNET4_OUTPUT_PER_M
  else:
    in_rate, out_rate = 3.0, 15.0
  return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


def log_judge_usage(
  path: Path,
  *,
  episode_id: str,
  model: str,
  usage: JudgeUsage,
  primary_mode: str,
) -> dict:
  row = {
    "episode_id": episode_id,
    "model": model,
    "input_tokens": usage.input_tokens,
    "output_tokens": usage.output_tokens,
    "estimated_cost_usd": round(usage.estimated_cost_usd, 6),
    "primary_mode": primary_mode,
  }
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
  return row


def summarize_judge_usage(rows: list[dict]) -> dict:
  if not rows:
    return {
      "judge_calls": 0,
      "input_tokens": 0,
      "output_tokens": 0,
      "estimated_cost_usd": 0.0,
    }
  return {
    "judge_calls": len(rows),
    "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
    "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
    "estimated_cost_usd": round(sum(r.get("estimated_cost_usd", 0.0) for r in rows), 4),
  }
