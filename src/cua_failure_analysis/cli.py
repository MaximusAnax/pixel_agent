"""CLI entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cua_failure_analysis.attribution.pipeline import attribute_directory
from cua_failure_analysis.judge.client import VLMJudgeConfig
from cua_failure_analysis.labeling.agreement import judge_vs_human_agreement, per_leaf_kappa
from cua_failure_analysis.labeling.gold_set import load_gold_jsonl, write_labeling_template
from cua_failure_analysis.stats.prevalence import prevalence_table


def attribute_cmd() -> None:
  p = argparse.ArgumentParser(description="Run hybrid failure attribution on traces")
  p.add_argument("--traces-root", type=Path, required=True)
  p.add_argument("--output", type=Path, required=True)
  p.add_argument("--judge-url", default=None)
  p.add_argument("--judge-model", default="opencua-7b")
  args = p.parse_args()
  cfg = None
  if args.judge_url:
    cfg = VLMJudgeConfig(base_url=args.judge_url, model=args.judge_model)
  attribute_directory(args.traces_root, args.output, judge_config=cfg)
  print(f"Wrote attributions to {args.output}")


def agreement_cmd() -> None:
  p = argparse.ArgumentParser(description="Compute inter-rater and judge agreement")
  p.add_argument("--gold", type=Path, required=True)
  p.add_argument("--output", type=Path, required=True)
  args = p.parse_args()
  gold = load_gold_jsonl(args.gold)
  kappas = per_leaf_kappa(gold)
  judge_report = None
  if gold and "judge_label" in gold[0] and "adjudicated_label" in gold[0]:
    judge_report = judge_vs_human_agreement(gold)
  report = {
    "per_leaf_kappa": kappas,
    "judge_vs_human": judge_report.__dict__ if judge_report else None,
  }
  args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
  print(f"Wrote agreement report to {args.output}")


def judge_cmd() -> None:
  attribute_cmd()


def prevalence_cmd() -> None:
  p = argparse.ArgumentParser(description="Compute failure prevalence table")
  p.add_argument("--attributions", type=Path, required=True)
  p.add_argument("--output", type=Path, required=True)
  p.add_argument("--model-id", default=None)
  args = p.parse_args()
  rows = []
  with args.attributions.open(encoding="utf-8") as f:
    for line in f:
      if line.strip():
        rows.append(json.loads(line))
  table = prevalence_table(rows, model_id=args.model_id)
  args.output.write_text(json.dumps(table, indent=2), encoding="utf-8")
  print(f"Wrote prevalence to {args.output}")


def trace_cmd() -> None:
  print("Use TraceLogger from cua_failure_analysis.trace.schema in OSWorld agent hooks.")
