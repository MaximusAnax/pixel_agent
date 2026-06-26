#!/usr/bin/env python3
"""Export a stratified human-labeling template from a pilot analysis run.

Reads the per-episode failure labels produced by ``hf_osworld_analyze.py`` and
samples a stratified set of first-failure steps toward the Phase D target of
150-200 steps with >=10 examples per leaf where feasible (failureStudyProtocol.md).

The output CSV uses the gold-set columns plus a few helper columns and pre-fills
the judge's provisional label. Human annotators fill ``annotator_a`` /
``annotator_b`` / ``adjudicated_label``; the provisional ``judge_label`` is kept
separate so it never contaminates the human pass.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from cua_failure_analysis.labeling.gold_set import GOLD_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
EXTRA_COLUMNS = ["episode_id", "normalized_trace_path", "tier_used", "confidence"]


def load_failed_labels(run_dir: Path) -> list[dict]:
  labels_path = run_dir / "failure_labels.jsonl"
  if not labels_path.exists():
    raise FileNotFoundError(f"No failure_labels.jsonl in {run_dir}")
  rows = []
  with labels_path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      row = json.loads(line)
      if row.get("status") == "failed" and row.get("primary_mode"):
        rows.append(row)
  return rows


def stratified_sample(
  rows: list[dict], per_leaf: int, max_total: int
) -> list[dict]:
  """Round-robin across leaves so rare leaves are not crowded out."""
  by_leaf: dict[str, list[dict]] = defaultdict(list)
  for row in rows:
    by_leaf[row["primary_mode"]].append(row)
  for leaf_rows in by_leaf.values():
    leaf_rows.sort(key=lambda r: r.get("episode_id", ""))

  selected: list[dict] = []
  leaves = sorted(by_leaf)
  cursor = {leaf: 0 for leaf in leaves}
  while len(selected) < max_total:
    progressed = False
    for leaf in leaves:
      idx = cursor[leaf]
      if idx >= min(per_leaf, len(by_leaf[leaf])):
        continue
      selected.append(by_leaf[leaf][idx])
      cursor[leaf] += 1
      progressed = True
      if len(selected) >= max_total:
        break
    if not progressed:
      break
  return selected


def to_template_row(row: dict) -> dict:
  episode_id = row.get("episode_id", "")
  task_id = episode_id.split("/", 1)[1] if "/" in episode_id else episode_id
  trace_id = episode_id.replace("/", "__") or task_id
  template = {col: "" for col in GOLD_COLUMNS + EXTRA_COLUMNS}
  template.update(
    {
      "trace_id": trace_id,
      "task_id": task_id,
      "seed": 0,
      "t_star": row.get("t_star", ""),
      "secondary_modes": ";".join(row.get("secondary_modes", []) or []),
      "propagated": row.get("propagated", False),
      "judge_label": row.get("primary_mode", ""),
      "episode_id": episode_id,
      "normalized_trace_path": f"normalized_traces/{episode_id}/trace.jsonl",
      "tier_used": row.get("tier_used", ""),
      "confidence": row.get("confidence", ""),
    }
  )
  return template


def write_template(path: Path, rows: list[dict]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=GOLD_COLUMNS + EXTRA_COLUMNS)
    writer.writeheader()
    for row in rows:
      writer.writerow(to_template_row(row))


def main() -> None:
  p = argparse.ArgumentParser(description="Export stratified gold-labeling template")
  p.add_argument("--run-dir", type=Path, required=True, help="data/babel_outputs/<run_id>")
  p.add_argument(
    "--output", type=Path, default=ROOT / "data" / "labeling" / "pilot_gold_candidates.csv"
  )
  p.add_argument("--per-leaf", type=int, default=12)
  p.add_argument("--max-total", type=int, default=200)
  args = p.parse_args()

  rows = load_failed_labels(args.run_dir)
  selected = stratified_sample(rows, args.per_leaf, args.max_total)
  write_template(args.output, selected)

  by_leaf = defaultdict(int)
  for row in selected:
    by_leaf[row["primary_mode"]] += 1
  print(f"Failed episodes available: {len(rows)}")
  print(f"Selected for labeling: {len(selected)} -> {args.output}")
  for leaf in sorted(by_leaf):
    print(f"  {leaf}: {by_leaf[leaf]}")


if __name__ == "__main__":
  main()
