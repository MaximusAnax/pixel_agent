"""Cost metering with a hard stop (the $25 gate, Decision 3).

The meter estimates cost BEFORE each judge call and raises BudgetExceeded
when the next call would cross the cap — the loop stops, it does not ask
forgiveness. Detector experiments are free and never metered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CHARS_PER_TOKEN = 4.0
DEFAULT_SESSION_CAP_USD = 25.0


class BudgetExceeded(RuntimeError):
  pass


@dataclass
class Pricing:
  input_per_mtok: float
  output_per_mtok: float
  image_tokens_each: int

  @classmethod
  def from_config(cls, pricing_path: Path, model: str,
                  screen_width: int = 1920, screen_height: int = 1080) -> "Pricing":
    cfg = yaml.safe_load(pricing_path.read_text(encoding="utf-8"))
    if model not in cfg.get("models", {}):
      raise ValueError(f"Model {model!r} missing from {pricing_path}")
    img_cfg = cfg.get("image_tokens", {})
    ppt = float(img_cfg.get("pixels_per_token", 750))
    max_edge = float(img_cfg.get("max_long_edge_px", 1568))
    w, h = screen_width, screen_height
    long_edge = max(w, h)
    if long_edge > max_edge:
      scale = max_edge / long_edge
      w, h = int(w * scale), int(h * scale)
    return cls(
      input_per_mtok=float(cfg["models"][model]["input_per_mtok"]),
      output_per_mtok=float(cfg["models"][model]["output_per_mtok"]),
      image_tokens_each=int(w * h / ppt),
    )

  @classmethod
  def free(cls) -> "Pricing":
    """Self-hosted vLLM endpoints: no marginal API cost, meter still counts calls."""
    return cls(input_per_mtok=0.0, output_per_mtok=0.0, image_tokens_each=0)


@dataclass
class CostMeter:
  pricing: Pricing
  cap_usd: float = DEFAULT_SESSION_CAP_USD
  spent_usd: float = 0.0
  calls: int = 0
  input_tokens: int = 0
  output_tokens: int = 0
  history: list[float] = field(default_factory=list)

  def estimate_call_usd(self, system: str, user: str, expected_output_tokens: int,
                        images: int = 0) -> float:
    in_tokens = int((len(system) + len(user)) / CHARS_PER_TOKEN) + 1
    in_tokens += images * self.pricing.image_tokens_each
    cost = (
      in_tokens / 1e6 * self.pricing.input_per_mtok
      + expected_output_tokens / 1e6 * self.pricing.output_per_mtok
    )
    return cost

  def charge_call(self, system: str, user: str, expected_output_tokens: int,
                  images: int = 0) -> float:
    cost = self.estimate_call_usd(system, user, expected_output_tokens, images)
    if self.spent_usd + cost > self.cap_usd:
      raise BudgetExceeded(
        f"Next call (~${cost:.4f}) would exceed cap ${self.cap_usd:.2f} "
        f"(spent ${self.spent_usd:.2f} over {self.calls} calls). "
        "Raise the cap only with Abdoul's approval (Decision 3)."
      )
    self.spent_usd += cost
    self.calls += 1
    self.input_tokens += int((len(system) + len(user)) / CHARS_PER_TOKEN) + 1
    self.input_tokens += images * self.pricing.image_tokens_each
    self.output_tokens += expected_output_tokens
    self.history.append(cost)
    return cost

  def as_dict(self) -> dict:
    return {
      "spent_usd": round(self.spent_usd, 4),
      "cap_usd": self.cap_usd,
      "calls": self.calls,
      "input_tokens": self.input_tokens,
      "output_tokens": self.output_tokens,
    }
