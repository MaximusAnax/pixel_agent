#!/usr/bin/env python3
"""Select episodes for taxonomy discovery review packets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from cua_failure_analysis.review.selection import (
  select_paired_pilot_episodes,
  select_review_episodes,
  write_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
  p = argparse.ArgumentParser(description="Select review episodes for taxonomy discovery")
  p.add_argument(
    "--run-dirs",
    type=Path,
    nargs="+",
    required=True,
    help="Two babel_outputs run dirs (a3b and 7b)",
  )
  p.add_argument(
    "--mode",
    choices=("paired-pilot", "stratified-failures"),
    default="paired-pilot",
    help="paired-pilot: all pilot tasks with both models (default)",
  )
  p.add_argument(
    "--tasks-file",
    type=Path,
    default=ROOT / "config" / "stratified_tasks.json",
  )
  p.add_argument("--phase", default="pilot", choices=("pilot", "core"))
  p.add_argument("--n-per-model", type=int, default=10)
  p.add_argument("--confusing-slots", type=int, default=3)
  p.add_argument("--packet-id", default="")
  p.add_argument("--output-dir", type=Path, default=None)
  args = p.parse_args()

  packet_id = args.packet_id or f"pilot_taxonomy_{datetime.now().strftime('%Y%m%d')}"
  output_dir = args.output_dir or (ROOT / "data" / "review_packets" / packet_id)
  manifest_path = output_dir / "manifest.json"

  task_groups: list[dict] | None = None
  if args.mode == "paired-pilot":
    if len(args.run_dirs) != 2:
      p.error("paired-pilot mode requires exactly two --run-dirs")
    episodes, task_groups = select_paired_pilot_episodes(
      args.run_dirs, tasks_file=args.tasks_file, phase=args.phase
    )
  else:
    episodes = select_review_episodes(
      args.run_dirs,
      n_per_model=args.n_per_model,
      confusing_slots=args.confusing_slots,
      mode="stratified-failures",
    )

  a3b_run = next((str(d) for d in args.run_dirs if "a3b" in d.name.lower()), None)
  b7_run = next((str(d) for d in args.run_dirs if "7b" in d.name.lower()), None)

  write_manifest(
    manifest_path,
    episodes,
    packet_id=packet_id,
    a3b_run=a3b_run,
    b7_run=b7_run,
    task_groups=task_groups,
    selection_mode=args.mode,
  )

  by_model: dict[str, int] = {}
  for ep in episodes:
    by_model[ep["model"]] = by_model.get(ep["model"], 0) + 1

  print(f"Selected {len(episodes)} episodes -> {manifest_path}")
  if task_groups is not None:
    print(f"  pilot tasks: {len(task_groups)}")
  for model, count in sorted(by_model.items()):
    print(f"  {model}: {count}")
  print(json.dumps({"packet_id": packet_id, "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
  main()
