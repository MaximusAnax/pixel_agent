#!/usr/bin/env python3
"""Run the autoresearch loop.

Offline (free, deterministic — the default):
  python scripts/run_loop.py --executor detector --proposals grid \
      --grid config/proposals_detector_grid.yaml --run-id det-001

Queue mode (human/agent-authored experiments):
  python scripts/run_loop.py --executor detector --proposals queue \
      --queue config/experiments_queue.yaml --run-id q-001

Live judge mode (needs a vLLM endpoint or API key; hard cost cap):
  python scripts/run_loop.py --executor judge --proposals queue \
      --queue config/experiments_queue.yaml --judge-url http://NODE:8000/v1 \
      --cap-usd 25 --run-id judge-001

LLM proposer (P2 — requires Abdoul's approval, see AGENTS.md):
  python scripts/run_loop.py ... --proposals llm --enable-llm-proposer
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "errorAnalysis" / "src"))

from auto_research.budget import CostMeter, Pricing  # noqa: E402
from auto_research.candidates import load_candidate  # noqa: E402
from auto_research.executors import DetectorExecutor, JudgeExecutor  # noqa: E402
from auto_research.loop import Ledger, LoopConfig, run_loop, write_summary  # noqa: E402
from auto_research.objective import load_eval_set  # noqa: E402
from auto_research.proposals import grid_proposals, llm_proposals, queue_proposals  # noqa: E402


def main() -> None:
  p = argparse.ArgumentParser(description="pixelAgent autoresearch loop")
  p.add_argument("--executor", choices=["detector", "judge"], default="detector")
  p.add_argument("--proposals", choices=["grid", "queue", "llm"], default="grid")
  p.add_argument("--baseline", type=Path, default=ROOT / "config" / "baseline_candidate.yaml")
  p.add_argument("--eval-set", type=Path, default=ROOT / "data" / "eval_set")
  p.add_argument("--grid", type=Path, default=ROOT / "config" / "proposals_detector_grid.yaml")
  p.add_argument("--queue", type=Path, default=ROOT / "config" / "experiments_queue.yaml")
  p.add_argument("--ledger", type=Path, default=ROOT / "data" / "ledger.jsonl")
  p.add_argument("--run-id", required=True)
  p.add_argument("--min-delta", type=float, default=0.005)
  p.add_argument("--max-experiments", type=int, default=200)
  p.add_argument("--judge-url", default=None, help="OpenAI-compatible endpoint (vLLM)")
  p.add_argument("--judge-api-key", default="EMPTY")
  p.add_argument("--cap-usd", type=float, default=25.0)
  p.add_argument("--pricing", type=Path,
                 default=ROOT.parent / "errorAnalysis" / "config" / "judge_pricing.yaml")
  p.add_argument("--priced-model", default=None,
                 help="pricing key when the judge model costs money (API judges)")
  p.add_argument("--enable-llm-proposer", action="store_true")
  p.add_argument("--max-llm-proposals", type=int, default=10)
  args = p.parse_args()

  eval_set = load_eval_set(args.eval_set)  # verifies content hash
  baseline = load_candidate(args.baseline)
  ledger = Ledger(args.ledger)
  config = LoopConfig(
    min_delta=args.min_delta,
    max_experiments=args.max_experiments,
    run_id=args.run_id,
    out_dir=ROOT / "data",
  )

  meter = None
  if args.executor == "judge":
    if args.priced_model:
      pricing = Pricing.from_config(args.pricing, args.priced_model)
    else:
      pricing = Pricing.free()  # self-hosted vLLM
    meter = CostMeter(pricing=pricing, cap_usd=args.cap_usd)
    try:
      from openai import OpenAI
    except ImportError:
      raise SystemExit("Judge executor needs the openai package (pip install openai)")
    if not args.judge_url:
      raise SystemExit("--judge-url is required for the judge executor")
    client = OpenAI(base_url=args.judge_url, api_key=args.judge_api_key)
    executor = JudgeExecutor(client=client, meter=meter,
                             erroranalysis_root=ROOT.parent / "errorAnalysis")
  else:
    executor = DetectorExecutor()

  if args.proposals == "grid":
    proposals = grid_proposals(baseline, args.grid)
  elif args.proposals == "queue":
    proposals = queue_proposals(baseline, args.queue)
  else:
    if not args.enable_llm_proposer:
      raise SystemExit(
        "--proposals llm needs --enable-llm-proposer (P2 gate; get Abdoul's "
        "approval first — see autoResearch/AGENTS.md)."
      )
    proposals = llm_proposals(
      baseline, ROOT / "program.md", ledger.tail(), max_proposals=args.max_llm_proposals
    )

  state = run_loop(baseline, proposals, executor, eval_set, ledger, config, meter=meter)
  summary = write_summary(state, eval_set, config, meter=meter)
  print(f"\nSummary: {summary}")
  print(
    f"Best: {state.best_candidate.name} calib={state.best_scores.calibration.primary:.4f} "
    f"holdout={state.best_scores.holdout.primary:.4f}"
  )


if __name__ == "__main__":
  main()
