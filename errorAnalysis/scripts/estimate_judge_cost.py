#!/usr/bin/env python3
"""Estimate frontier-model error-analysis cost against the $25 gate.

PROJECT_STATE action item: "After trajectories collected, ask agent to compute
token-cost estimate for frontier-model error analysis; proceed per $25
threshold" (Decision 3: <= $25 proceed, > $25 check with Matt).

Walks a traces root, counts failed runs (attribution only judges failures),
estimates prompt/output tokens per judge call from the actual trace contents,
and prices the run per model in config/judge_pricing.yaml.

Usage:
  python scripts/estimate_judge_cost.py --traces-root data/traces \
      --model claude-sonnet-4-6 [--protocol v2] [--images-per-call 1] \
      [--calls-per-run 1] [--output data/cost_estimate.json]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHARS_PER_TOKEN = 4.0  # standard rough heuristic for English/JSON text
GATE_USD = 25.0


@dataclass
class CostEstimate:
  model: str
  n_runs_total: int
  n_runs_failed: int
  calls: int
  input_tokens: int
  output_tokens: int
  image_tokens: int
  cost_usd: float
  cost_usd_batch: float
  gate_usd: float
  verdict: str
  pricing_as_of: str


def image_tokens_per_image(cfg: dict, width: int = 1920, height: int = 1080) -> int:
  img_cfg = cfg.get("image_tokens", {})
  ppt = float(img_cfg.get("pixels_per_token", 750))
  max_edge = float(img_cfg.get("max_long_edge_px", 1568))
  long_edge = max(width, height)
  if long_edge > max_edge:
    scale = max_edge / long_edge
    width, height = int(width * scale), int(height * scale)
  return int(width * height / ppt)


def _text_tokens(text: str) -> int:
  return int(len(text) / CHARS_PER_TOKEN) + 1


def estimate_tokens_for_trace(
  trace_path: Path,
  system_prompt_tokens: int,
  images_per_call: int,
  image_tokens: int,
  prev_steps_k: int = 3,
  protocol: str = "v1",
) -> tuple[int, int]:
  """Return (text_input_tokens, image_input_tokens) for one judge call."""
  lines = [ln for ln in trace_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
  if not lines:
    return (system_prompt_tokens, 0)
  steps = [json.loads(ln) for ln in lines]
  target = steps[-1]
  prev = steps[max(0, len(steps) - 1 - prev_steps_k) : len(steps) - 1]

  text = target.get("cot", "") + json.dumps(target.get("action", {}))
  text += "".join((s.get("cot", "") or "")[:120] for s in prev)
  text += target.get("instruction", "") or (steps[0].get("instruction", "") or "")
  if protocol == "v2":
    # reference trajectory summary + score + evaluator output roughly doubles
    # the per-call trajectory text
    text += "".join((s.get("cot", "") or "")[:120] for s in steps)
  tokens = system_prompt_tokens + _text_tokens(text)
  return (tokens, images_per_call * image_tokens)


def estimate(
  traces_root: Path,
  model: str,
  pricing_path: Path,
  protocol: str = "v1",
  images_per_call: int = 1,
  calls_per_run: int = 1,
  expected_output_tokens: int = 256,
  screen_width: int = 1920,
  screen_height: int = 1080,
) -> CostEstimate:
  cfg = yaml.safe_load(pricing_path.read_text(encoding="utf-8"))
  if model not in cfg.get("models", {}):
    raise SystemExit(f"Model {model!r} not in {pricing_path}; add pricing first.")
  prices = cfg["models"][model]
  img_tokens = image_tokens_per_image(cfg, screen_width, screen_height)

  # System prompt size measured from the real builders.
  import sys

  sys.path.insert(0, str(ROOT / "src"))
  from cua_failure_analysis.judge.prompts import (  # noqa: E402
    build_system_prompt,
    build_system_prompt_v2,
  )

  anchors = ROOT / "config" / "judge_anchors.yaml"
  system_prompt = (
    build_system_prompt_v2(anchors) if protocol == "v2" else build_system_prompt(anchors)
  )
  system_tokens = _text_tokens(system_prompt)

  n_total = n_failed = 0
  text_in = img_in = 0
  for trace_path in sorted(traces_root.glob("**/trace.jsonl")):
    n_total += 1
    manifest_path = trace_path.parent / "manifest.json"
    success = None
    if manifest_path.exists():
      success = json.loads(manifest_path.read_text(encoding="utf-8")).get("success")
    if success is True:
      continue
    n_failed += 1
    t_text, t_img = estimate_tokens_for_trace(
      trace_path, system_tokens, images_per_call, img_tokens, protocol=protocol
    )
    text_in += t_text * calls_per_run
    img_in += t_img * calls_per_run

  calls = n_failed * calls_per_run
  input_tokens = text_in + img_in
  output_tokens = calls * expected_output_tokens
  cost = (
    input_tokens / 1e6 * prices["input_per_mtok"]
    + output_tokens / 1e6 * prices["output_per_mtok"]
  )
  batch_cost = cost * float(cfg.get("batch_discount", 0.5))
  verdict = (
    "proceed (<= $%.0f gate)" % GATE_USD
    if cost <= GATE_USD
    else "check with Matt (> $%.0f gate); batch API would cost $%.2f" % (GATE_USD, batch_cost)
  )
  return CostEstimate(
    model=model,
    n_runs_total=n_total,
    n_runs_failed=n_failed,
    calls=calls,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    image_tokens=img_in,
    cost_usd=round(cost, 2),
    cost_usd_batch=round(batch_cost, 2),
    gate_usd=GATE_USD,
    verdict=verdict,
    pricing_as_of=str(cfg.get("as_of", "unknown")),
  )


def main() -> None:
  p = argparse.ArgumentParser(description="Judge cost estimate vs $25 gate")
  p.add_argument("--traces-root", type=Path, default=ROOT / "data" / "traces")
  p.add_argument("--model", default="claude-sonnet-4-6")
  p.add_argument("--pricing", type=Path, default=ROOT / "config" / "judge_pricing.yaml")
  p.add_argument("--protocol", choices=["v1", "v2"], default="v2")
  p.add_argument("--images-per-call", type=int, default=1)
  p.add_argument("--calls-per-run", type=int, default=1)
  p.add_argument("--expected-output-tokens", type=int, default=256)
  p.add_argument("--output", type=Path, default=None)
  args = p.parse_args()

  est = estimate(
    traces_root=args.traces_root,
    model=args.model,
    pricing_path=args.pricing,
    protocol=args.protocol,
    images_per_call=args.images_per_call,
    calls_per_run=args.calls_per_run,
    expected_output_tokens=args.expected_output_tokens,
  )
  payload = asdict(est)
  print(json.dumps(payload, indent=2))
  if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
  main()
