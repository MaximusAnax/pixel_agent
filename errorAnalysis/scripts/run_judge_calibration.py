#!/usr/bin/env python3
"""Run judge calibration against gold labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cua_failure_analysis.labeling.agreement import judge_vs_human_agreement
from cua_failure_analysis.labeling.gold_set import load_gold_jsonl

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
  p = argparse.ArgumentParser(description="Judge calibration against gold labels")
  p.add_argument("--gold", type=Path, default=ROOT / "data" / "labeling" / "example_gold_labels.jsonl")
  p.add_argument("--output", type=Path, default=ROOT / "data" / "labeling" / "calibration_report.json")
  args = p.parse_args()

  gold = load_gold_jsonl(args.gold)
  report = judge_vs_human_agreement(gold).__dict__
  report["n_gold"] = len(gold)

  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
  print(f"Calibration report: {args.output}")


if __name__ == "__main__":
  main()
