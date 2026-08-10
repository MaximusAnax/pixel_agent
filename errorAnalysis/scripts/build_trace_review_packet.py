#!/usr/bin/env python3
"""Build static HTML trace review packets from HF trajectory zips."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cua_failure_analysis.review.packet import build_review_packet

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = ROOT / "templates" / "trace_review"


def _infer_select_turn(run_dir: Path) -> str | None:
  meta_path = run_dir / "run_metadata.json"
  if not meta_path.exists():
    return None
  meta = json.loads(meta_path.read_text(encoding="utf-8"))
  return meta.get("selected_turn")


def main() -> None:
  p = argparse.ArgumentParser(description="Build HTML trace review packet")
  p.add_argument(
    "--manifest",
    type=Path,
    required=True,
    help="manifest.json from select_review_episodes.py",
  )
  p.add_argument(
    "--zip-a3b",
    type=Path,
    required=True,
    help="Path to OpenCUA A3B HF zip on this machine",
  )
  p.add_argument(
    "--zip-7b",
    type=Path,
    default=None,
    help="Path to OpenCUA 7B HF zip (required if manifest includes 7b episodes)",
  )
  p.add_argument(
    "--output-dir",
    type=Path,
    default=None,
    help="Defaults to manifest parent directory",
  )
  p.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
  p.add_argument(
    "--stratified-tasks",
    type=Path,
    default=ROOT / "config" / "stratified_tasks.json",
  )
  p.add_argument(
    "--oracle-root",
    type=Path,
    default=None,
    help="Partner Human Agent artifacts root (or set ORACLE_ROOT). "
    "Layout: <root>/<domain>/<task_id>/human_traj.json",
  )
  args = p.parse_args()

  output_dir = args.output_dir or args.manifest.parent
  manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

  zip_paths: dict[str, Path] = {"a3b": args.zip_a3b}
  if args.zip_7b:
    zip_paths["7b"] = args.zip_7b

  models_needed = {ep["model"] for ep in manifest.get("episodes", [])}
  for model in models_needed:
    if model not in zip_paths:
      raise SystemExit(f"Missing --zip-{model} for episodes in manifest")

  select_turns: dict[str, str] = {}
  for ep in manifest.get("episodes", []):
    model = ep["model"]
    if model in select_turns:
      continue
    run_dir = Path(ep.get("run_dir", ""))
    if run_dir.is_dir():
      turn = _infer_select_turn(run_dir)
      if turn:
        select_turns[model] = turn

  out = build_review_packet(
    args.manifest,
    zip_paths=zip_paths,
    output_dir=output_dir,
    template_dir=args.template_dir,
    stratified_tasks=args.stratified_tasks if args.stratified_tasks.exists() else None,
    select_turns=select_turns or None,
    oracle_root=args.oracle_root,
  )
  print(f"Review packet built: {out / 'index.html'}")


if __name__ == "__main__":
  main()
