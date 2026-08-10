#!/usr/bin/env python3
"""Score a single candidate against the frozen eval set (no loop, no ledger).

  python scripts/score_candidate.py --candidate config/baseline_candidate.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "errorAnalysis" / "src"))

from auto_research.candidates import load_candidate  # noqa: E402
from auto_research.executors import DetectorExecutor  # noqa: E402
from auto_research.loop import evaluate_candidate  # noqa: E402
from auto_research.objective import load_eval_set  # noqa: E402


def main() -> None:
  p = argparse.ArgumentParser(description="Score one candidate (detector executor)")
  p.add_argument("--candidate", type=Path, required=True)
  p.add_argument("--eval-set", type=Path, default=ROOT / "data" / "eval_set")
  args = p.parse_args()

  eval_set = load_eval_set(args.eval_set)
  candidate = load_candidate(args.candidate)
  scores = evaluate_candidate(candidate, DetectorExecutor(), eval_set)
  print(json.dumps(
    {
      "candidate": candidate.name,
      "candidate_hash": candidate.content_hash(),
      "eval_set_hash": eval_set.content_hash,
      **scores.as_dict(),
    },
    indent=2,
  ))


if __name__ == "__main__":
  main()
