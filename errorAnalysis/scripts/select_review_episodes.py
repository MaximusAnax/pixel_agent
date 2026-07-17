#!/usr/bin/env python3
"""Select episodes for taxonomy discovery review packets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from cua_failure_analysis.review.selection import (
  load_offline_judge,
  select_paired_all_episodes,
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
    nargs="*",
    default=[],
    help="Two babel_outputs run dirs (a3b and 7b); optional judge-metadata source in paired-all mode",
  )
  p.add_argument(
    "--mode",
    choices=("paired-pilot", "stratified-failures", "paired-all"),
    default="paired-pilot",
    help="paired-pilot: all pilot tasks with both models (default); "
    "paired-all: every task in the zips, plus OSWorld-Human replays with --gold-root",
  )
  p.add_argument("--zip-a3b", type=Path, default=None, help="A3B HF zip (paired-all mode)")
  p.add_argument("--zip-7b", type=Path, default=None, help="7B HF zip (paired-all mode)")
  p.add_argument(
    "--gold-root",
    type=Path,
    default=None,
    help="OSWorld-Human guided replay root (gold/<task_id>/) to pair as a 'human' trace",
  )
  p.add_argument(
    "--select-turn-7b",
    default=None,
    help="Which turn_N to use from a multi-attempt 7B zip (default: lowest present)",
  )
  p.add_argument(
    "--offline-judge",
    action="append",
    default=[],
    metavar="NAME=PATH",
    help="Attach offline whole-trajectory judge labels (trajectory_judge "
    "classifications JSONL); repeatable, same NAME merges multiple files "
    "(paired-all mode)",
  )
  p.add_argument(
    "--label-batch",
    type=Path,
    default=None,
    help="Text file of task ids (one per line, # comments) to mark as the "
    "active annotation batch; the index gets a 'label batch' filter for them",
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
  if args.mode == "paired-all":
    if not (args.zip_a3b and args.zip_7b):
      p.error("paired-all mode requires --zip-a3b and --zip-7b")
    select_turns = {"7b": args.select_turn_7b} if args.select_turn_7b else None
    offline_judges: dict[str, dict] = {}
    for spec in args.offline_judge:
      name, _, path = spec.partition("=")
      if not (name and path):
        p.error(f"--offline-judge expects NAME=PATH, got {spec!r}")
      offline_judges.setdefault(name, {}).update(load_offline_judge(Path(path)))
    episodes, task_groups = select_paired_all_episodes(
      {"a3b": args.zip_a3b, "7b": args.zip_7b},
      run_dirs=args.run_dirs,
      gold_root=args.gold_root,
      select_turns=select_turns,
      offline_judges=offline_judges or None,
    )
  elif args.mode == "paired-pilot":
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

  batch_ids: list[str] = []
  if args.label_batch:
    batch_ids = [
      line.strip()
      for line in args.label_batch.read_text(encoding="utf-8").splitlines()
      if line.strip() and not line.strip().startswith("#")
    ]
    if task_groups is not None:
      known = {g["task_id"] for g in task_groups}
      missing = [t for t in batch_ids if t not in known]
      if missing:
        raise SystemExit(f"--label-batch task ids not in selection: {missing}")
      for group in task_groups:
        group["in_label_batch"] = group["task_id"] in batch_ids

  write_manifest(
    manifest_path,
    episodes,
    packet_id=packet_id,
    a3b_run=a3b_run,
    b7_run=b7_run,
    task_groups=task_groups,
    selection_mode=args.mode,
    label_batch=batch_ids,
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
