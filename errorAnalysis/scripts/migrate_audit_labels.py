#!/usr/bin/env python3
"""Import gold-audit notes from the standalone viewer into packet annotations.

The gold audit viewer stored ``{task_id: {category, note, updated}}`` in a flat,
single-user ``audit_labels.json``. This merges those into the packet's shared
``annotations.json`` under one annotator's ``replay_audit`` block, after which
the standalone viewer is redundant.

Existing notes for the same task are kept when they are newer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cua_failure_analysis.review.annotations import (  # noqa: E402
  REPLAY_AUDIT_CATEGORIES,
  annotations_lock,
  get_replay_audit,
  load_annotations,
  save_annotations,
  validate_annotator_id,
)


def _normalize_timestamp(raw: str) -> str:
  """``2026-07-16 01:59Z`` (audit viewer) -> ISO-8601, so merges compare right."""
  raw = str(raw or "").strip()
  if not raw:
    return ""
  if raw.endswith("Z") and " " in raw:
    date, _, time = raw[:-1].partition(" ")
    return f"{date}T{time}:00+00:00" if time.count(":") == 1 else f"{date}T{time}+00:00"
  return raw


def main() -> int:
  p = argparse.ArgumentParser(description="Import audit_labels.json into annotations.json")
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument("--audit-labels", type=Path, required=True, help="Path to audit_labels.json")
  p.add_argument(
    "--annotator", required=True, help="Annotator to file these notes under (they were single-user)"
  )
  p.add_argument("--dry-run", action="store_true")
  args = p.parse_args()

  validate_annotator_id(args.annotator)
  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  live_path = packet_dir / "annotations.json"
  if not packet_dir.exists():
    raise SystemExit(f"Packet not found: {packet_dir}")

  incoming = json.loads(args.audit_labels.read_text(encoding="utf-8"))
  if not isinstance(incoming, dict):
    raise SystemExit(f"Expected an object in {args.audit_labels}")

  with annotations_lock(live_path):
    data = load_annotations(live_path, packet_id=args.packet_id, packet_dir=packet_dir)
    current = get_replay_audit(data, args.annotator)
    added = updated = skipped = 0

    for task_id, entry in incoming.items():
      if not isinstance(entry, dict):
        continue
      category = str(entry.get("category") or "")
      if category and category not in REPLAY_AUDIT_CATEGORIES:
        print(f"  ! unknown category {category!r} on {task_id}; importing as-is", file=sys.stderr)
      item = {
        "category": category,
        "note": str(entry.get("note") or ""),
        "updated_at": _normalize_timestamp(entry.get("updated")),
      }
      existing = current.get(str(task_id))
      if existing is None:
        added += 1
      elif str(existing.get("updated_at") or "") > item["updated_at"]:
        skipped += 1
        continue
      else:
        updated += 1
      current[str(task_id)] = item

    data["annotators"][args.annotator]["replay_audit"] = current
    if args.dry_run:
      print(f"[dry run] would write {len(current)} notes for {args.annotator}")
    else:
      save_annotations(live_path, data)

  print(f"{added} added, {updated} updated, {skipped} kept (newer already present)")
  print(f"annotations: {live_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
