#!/usr/bin/env python3
"""Estimate frontier-judge cost for a planned run and guard against overspend.

Extrapolates the per-call token cost observed in a reference run's
``judge_usage.jsonl`` to a projected number of judge calls, then compares the
estimate against a ceiling (default $25, per the project action items). Exits
non-zero when the estimate exceeds the ceiling so it can gate a submit script.

Example:
  python scripts/estimate_judge_cost.py \\
    --reference-run-dir data/babel_outputs/<pilot_run> \\
    --projected-judge-calls 250 --ceiling-usd 25
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cua_failure_analysis.judge.usage import estimate_judge_cost_usd, summarize_judge_usage

ROOT = Path(__file__).resolve().parents[1]


def load_usage_rows(run_dir: Path) -> list[dict]:
  path = run_dir / "judge_usage.jsonl"
  if not path.exists():
    raise FileNotFoundError(f"No judge_usage.jsonl in {run_dir}")
  rows = []
  with path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        rows.append(json.loads(line))
  return rows


def count_failed_episodes(run_dir: Path) -> int:
  path = run_dir / "failure_labels.jsonl"
  if not path.exists():
    return 0
  count = 0
  with path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line and json.loads(line).get("status") == "failed":
        count += 1
  return count


def main() -> int:
  p = argparse.ArgumentParser(description="Estimate judge cost and guard a ceiling")
  p.add_argument(
    "--reference-run-dir",
    type=Path,
    required=True,
    help="Run dir with judge_usage.jsonl used to derive per-call token averages.",
  )
  group = p.add_mutually_exclusive_group(required=True)
  group.add_argument("--projected-judge-calls", type=int, help="Expected number of judge calls.")
  group.add_argument(
    "--projected-run-dir",
    type=Path,
    help="Estimate judge calls from a run dir's failed-episode count x judge rate.",
  )
  p.add_argument(
    "--judge-rate",
    type=float,
    default=None,
    help="Fraction of failed episodes reaching the judge (default: inferred from reference).",
  )
  p.add_argument(
    "--ceiling-usd",
    type=float,
    default=float(__import__("os").environ.get("JUDGE_COST_CEILING_USD", "25")),
  )
  args = p.parse_args()

  rows = load_usage_rows(args.reference_run_dir)
  summary = summarize_judge_usage(rows)
  n_calls = max(1, summary["judge_calls"])
  avg_in = summary["input_tokens"] / n_calls
  avg_out = summary["output_tokens"] / n_calls
  model = rows[-1].get("model", "claude")
  per_call_cost = estimate_judge_cost_usd(model, round(avg_in), round(avg_out))

  ref_failed = count_failed_episodes(args.reference_run_dir)
  inferred_rate = (summary["judge_calls"] / ref_failed) if ref_failed else 1.0
  judge_rate = args.judge_rate if args.judge_rate is not None else inferred_rate

  if args.projected_judge_calls is not None:
    projected_calls = args.projected_judge_calls
    basis = "explicit --projected-judge-calls"
  else:
    projected_failed = count_failed_episodes(args.projected_run_dir)
    projected_calls = round(projected_failed * judge_rate)
    basis = (
      f"{projected_failed} failed episodes x judge_rate {judge_rate:.2f}"
    )

  estimate = projected_calls * per_call_cost

  print(f"Reference run: {args.reference_run_dir}")
  print(f"  calls={summary['judge_calls']} avg_in={avg_in:.0f} avg_out={avg_out:.0f} model={model}")
  print(f"  per-call cost: ${per_call_cost:.4f}")
  print(f"Projection basis: {basis}")
  print(f"Projected judge calls: {projected_calls}")
  print(f"Estimated cost: ${estimate:.2f} (ceiling ${args.ceiling_usd:.2f})")

  if estimate > args.ceiling_usd:
    print(
      f"BLOCK: estimate ${estimate:.2f} exceeds ceiling ${args.ceiling_usd:.2f}. "
      "Raise --ceiling-usd or check with Matt before scaling.",
      file=sys.stderr,
    )
    return 1
  print("OK: estimate within ceiling.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
