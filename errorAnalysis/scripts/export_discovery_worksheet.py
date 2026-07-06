#!/usr/bin/env python3
"""Export taxonomy discovery worksheet CSV (judge + human labels)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cua_failure_analysis.review.discovery import DISCOVERY_COLUMNS
from cua_failure_analysis.review.labels import build_discovery_row, load_human_labels

ROOT = Path(__file__).resolve().parents[1]


def manifest_to_rows(manifest_path: Path, human_labels_path: Path | None) -> list[dict]:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  if human_labels_path is None:
    human_labels_path = manifest_path.parent / "human_labels.json"
  human = load_human_labels(human_labels_path)

  rows: list[dict] = []
  for ep in manifest.get("episodes", []):
    model = ep.get("model", "")
    episode_id = ep["episode_id"]
    key = f"{model}/{episode_id.replace('/', '__')}"
    rows.append(build_discovery_row(ep, human.get(key), columns=DISCOVERY_COLUMNS))
  return rows


def main() -> None:
  p = argparse.ArgumentParser(description="Export taxonomy discovery labeling worksheet")
  p.add_argument("--manifest", type=Path, help="packet_manifest.json")
  p.add_argument("--human-labels", type=Path, default=None)
  p.add_argument(
    "--output",
    type=Path,
    default=ROOT / "data" / "labeling" / "taxonomy_discovery_labels.csv",
  )
  args = p.parse_args()

  manifest_path = args.manifest
  if manifest_path is None:
    packets = sorted((ROOT / "data" / "review_packets").glob("*/packet_manifest.json"))
    if not packets:
      raise SystemExit("No packet_manifest.json found; pass --manifest")
    manifest_path = packets[-1]

  rows = manifest_to_rows(manifest_path, args.human_labels)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=DISCOVERY_COLUMNS)
    writer.writeheader()
    for row in rows:
      writer.writerow(row)

  labeled = sum(1 for r in rows if r.get("human_modes_ordered"))
  print(f"Wrote {len(rows)} rows ({labeled} with human labels) -> {args.output}")


if __name__ == "__main__":
  main()
