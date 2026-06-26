#!/usr/bin/env python3
"""Aggregate per-episode failure labels into a provisional prevalence report.

Consumes the ``failure_labels.jsonl`` from one analysis run and emits:
- per-leaf prevalence at t* with Wilson confidence intervals (overall + per model);
- a co-occurrence matrix between primary and secondary modes;
- propagation rates for consequence leaves (Action Looping, Long-Horizon Memory);
- task-tag-gated leaves restricted to their matching tagged tasks.

All outputs are provisional until human gold calibration (Phase D); the report
records that explicitly.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from cua_failure_analysis.stats.prevalence import prevalence_table, wilson_ci
from cua_failure_analysis.taxonomy import TASK_TAG_GATED, FailureLeaf

ROOT = Path(__file__).resolve().parents[1]
CONSEQUENCE_LEAVES = [
  FailureLeaf.ACTION_LOOPING.value,
  FailureLeaf.LONG_HORIZON_MEMORY.value,
]


def load_failed_labels(run_dir: Path) -> list[dict]:
  labels_path = run_dir / "failure_labels.jsonl"
  if not labels_path.exists():
    raise FileNotFoundError(f"No failure_labels.jsonl in {run_dir}")
  rows = []
  with labels_path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        row = json.loads(line)
        if row.get("status") == "failed" and row.get("primary_mode"):
          rows.append(row)
  return rows


def load_task_tags(tasks_file: Path) -> dict[str, list[str]]:
  if not tasks_file.exists():
    return {}
  data = json.loads(tasks_file.read_text(encoding="utf-8"))
  return {
    t["task_id"]: list(t.get("task_tags") or [])
    for t in data.get("tasks", [])
    if t.get("task_id")
  }


def _task_id(row: dict) -> str:
  episode_id = row.get("episode_id", "")
  return episode_id.split("/", 1)[1] if "/" in episode_id else episode_id


def cooccurrence(rows: list[dict]) -> dict[str, dict[str, int]]:
  matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
  for row in rows:
    primary = row["primary_mode"]
    for secondary in row.get("secondary_modes", []) or []:
      matrix[primary][secondary] += 1
  return {k: dict(v) for k, v in matrix.items()}


def propagation_rates(rows: list[dict]) -> dict[str, dict]:
  out = {}
  for leaf in CONSEQUENCE_LEAVES:
    leaf_rows = [r for r in rows if r["primary_mode"] == leaf]
    n = len(leaf_rows)
    prop = sum(1 for r in leaf_rows if r.get("propagated"))
    lo, hi = wilson_ci(prop, n)
    out[leaf] = {
      "n": n,
      "propagated": prop,
      "rate": prop / n if n else 0.0,
      "ci_low": lo,
      "ci_high": hi,
    }
  return out


def gated_leaf_prevalence(rows: list[dict], tags: dict[str, list[str]]) -> dict[str, dict]:
  out = {}
  for leaf, required_tag in TASK_TAG_GATED.items():
    tagged_rows = [r for r in rows if required_tag in tags.get(_task_id(r), [])]
    n = len(tagged_rows)
    count = sum(1 for r in tagged_rows if r["primary_mode"] == leaf.value)
    lo, hi = wilson_ci(count, n)
    out[leaf.value] = {
      "required_tag": required_tag,
      "n_tagged_failures": n,
      "count": count,
      "prevalence_on_tagged": count / n if n else 0.0,
      "ci_low": lo,
      "ci_high": hi,
    }
  return out


def main() -> None:
  p = argparse.ArgumentParser(description="Provisional failure prevalence report")
  p.add_argument("--run-dir", type=Path, required=True, help="data/babel_outputs/<run_id>")
  p.add_argument("--output", type=Path, default=None, help="JSON output path")
  p.add_argument("--tasks-file", type=Path, default=ROOT / "config" / "stratified_tasks.json")
  args = p.parse_args()

  rows = load_failed_labels(args.run_dir)
  tags = load_task_tags(args.tasks_file)
  models = sorted({r.get("model_id", "") for r in rows})

  report = {
    "run_dir": str(args.run_dir),
    "n_failed_episodes": len(rows),
    "models": models,
    "provisional": True,
    "note": "Provisional until human gold calibration (Phase D).",
    "prevalence_overall": prevalence_table(rows),
    "prevalence_by_model": {m: prevalence_table(rows, model_id=m) for m in models},
    "cooccurrence": cooccurrence(rows),
    "propagation": propagation_rates(rows),
    "gated_leaf_prevalence": gated_leaf_prevalence(rows, tags),
    "tier_used_counts": dict(Counter(r.get("tier_used", "") for r in rows)),
  }

  output = args.output or (args.run_dir / "prevalence_report.json")
  output.parent.mkdir(parents=True, exist_ok=True)
  output.write_text(json.dumps(report, indent=2), encoding="utf-8")
  print(f"Wrote prevalence report: {output}")
  print(f"Failed episodes: {len(rows)} | models: {models}")
  for entry in report["prevalence_overall"]:
    if entry["count"]:
      print(
        f"  {entry['leaf']}: {entry['count']}/{entry['n_failures']} "
        f"({entry['prevalence']:.2f}, CI [{entry['ci_low']:.2f}, {entry['ci_high']:.2f}])"
      )


if __name__ == "__main__":
  main()
