#!/usr/bin/env python3
"""Export wide taxonomy discovery worksheet (judge + two annotators)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cua_failure_analysis.review.annotations import (
  ANNOTATIONS_FILENAME,
  REGISTERED_ANNOTATORS,
  get_annotator_labels,
  load_annotations,
)
from cua_failure_analysis.review.discovery import comparison_columns
from cua_failure_analysis.review.labels import build_comparison_row, label_storage_key

ROOT = Path(__file__).resolve().parents[1]


def manifest_to_comparison_rows(
  manifest_path: Path,
  annotations_path: Path,
  *,
  annotator_a: str,
  annotator_b: str,
) -> list[dict[str, str]]:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  data = load_annotations(annotations_path, packet_dir=manifest_path.parent)
  labels_a = get_annotator_labels(data, annotator_a)
  labels_b = get_annotator_labels(data, annotator_b)
  columns = comparison_columns(annotator_a, annotator_b)

  rows: list[dict[str, str]] = []
  for ep in manifest.get("episodes", []):
    model = ep.get("model", "")
    episode_id = ep["episode_id"]
    key = label_storage_key(model, episode_id)
    rows.append(
      build_comparison_row(
        ep,
        human_a=labels_a.get(key),
        human_b=labels_b.get(key),
        annotator_a=annotator_a,
        annotator_b=annotator_b,
        columns=columns,
      )
    )
  return rows


def main() -> None:
  p = argparse.ArgumentParser(description="Export judge + two-annotator comparison CSV")
  p.add_argument("--manifest", type=Path, help="packet_manifest.json")
  p.add_argument("--annotations", type=Path, default=None)
  p.add_argument("--annotator-a", default=REGISTERED_ANNOTATORS[0])
  p.add_argument("--annotator-b", default=REGISTERED_ANNOTATORS[1])
  p.add_argument(
    "--output",
    type=Path,
    default=ROOT / "data" / "labeling" / "discovery_comparison_abdoul_raghav.csv",
  )
  args = p.parse_args()

  manifest_path = args.manifest
  if manifest_path is None:
    packets = sorted((ROOT / "data" / "review_packets").glob("*/packet_manifest.json"))
    if not packets:
      raise SystemExit("No packet_manifest.json found; pass --manifest")
    manifest_path = packets[-1]

  annotations_path = args.annotations or manifest_path.parent / ANNOTATIONS_FILENAME
  columns = comparison_columns(args.annotator_a, args.annotator_b)
  rows = manifest_to_comparison_rows(
    manifest_path,
    annotations_path,
    annotator_a=args.annotator_a,
    annotator_b=args.annotator_b,
  )

  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    for row in rows:
      writer.writerow(row)

  labeled_a = sum(1 for r in rows if r.get(f"{args.annotator_a}_primary"))
  labeled_b = sum(1 for r in rows if r.get(f"{args.annotator_b}_primary"))
  print(
    f"Wrote {len(rows)} rows ({labeled_a} {args.annotator_a}, "
    f"{labeled_b} {args.annotator_b} labeled) -> {args.output}"
  )


if __name__ == "__main__":
  main()
