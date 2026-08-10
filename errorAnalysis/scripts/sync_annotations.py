#!/usr/bin/env python3
"""Sync review packet annotations with a git-tracked snapshot.

The live labels are ``<packet_dir>/annotations.json`` (shared between
annotators when the packet dir lives in group storage). This script mirrors
them into ``errorAnalysis/annotations/<packet_id>.json`` — a committed file —
so labels can travel through GitHub between checkouts/machines.

  push: merge live -> snapshot (newest updated_at wins), git add + commit.
        Run ``git push`` afterwards (or pass --git-push).
  pull: merge snapshot -> live. Run ``git pull`` first to get the partner's
        latest snapshot.

Merging is per (annotator, episode); nothing is ever dropped, so push/pull are
safe to run in any order from any checkout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from cua_failure_analysis.review.annotations import (
  annotations_lock,
  load_annotations,
  merge_annotations,
  save_annotations,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "annotations"


def _labels_count(data: dict) -> dict[str, str]:
  return {
    aid: f"{len(block.get('labels') or {})} labels, "
    f"{len(block.get('replay_audit') or {})} replay notes"
    for aid, block in (data.get("annotators") or {}).items()
  }


def main() -> int:
  p = argparse.ArgumentParser(description="Sync packet annotations with the git snapshot")
  p.add_argument("action", choices=("push", "pull"))
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument(
    "--git-push",
    action="store_true",
    help="push: also run 'git push' after committing the snapshot",
  )
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  live_path = packet_dir / "annotations.json"
  snapshot_path = SNAPSHOT_DIR / f"{args.packet_id}.json"
  if not packet_dir.exists():
    raise SystemExit(f"Packet not found: {packet_dir}")

  with annotations_lock(live_path):
    live = load_annotations(live_path, packet_id=args.packet_id, packet_dir=packet_dir)
    snapshot = (
      load_annotations(snapshot_path, packet_id=args.packet_id)
      if snapshot_path.exists()
      else None
    )
    merged = merge_annotations(snapshot, live) if snapshot else live

    if args.action == "push":
      SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
      snapshot_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
      save_annotations(live_path, merged)
      rel = snapshot_path.relative_to(ROOT.parent)
      subprocess.run(["git", "add", str(rel)], cwd=ROOT.parent, check=True)
      committed = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", str(rel)], cwd=ROOT.parent
      ).returncode
      if committed:
        subprocess.run(
          ["git", "commit", "-m", f"annotations: sync {args.packet_id} snapshot"],
          cwd=ROOT.parent,
          check=True,
        )
        print(f"Committed snapshot {rel} — run 'git push' to publish", file=sys.stderr)
        if args.git_push:
          subprocess.run(["git", "push"], cwd=ROOT.parent, check=True)
      else:
        print("Snapshot already up to date; nothing committed", file=sys.stderr)
    else:  # pull
      if snapshot is None:
        raise SystemExit(f"No snapshot at {snapshot_path}; did you 'git pull'?")
      save_annotations(live_path, merged)

  print(f"live labels:     {_labels_count(merged)}")
  print(f"live file:       {live_path}")
  print(f"snapshot file:   {snapshot_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
