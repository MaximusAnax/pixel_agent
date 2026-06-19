"""Gold set loading and export."""

from __future__ import annotations

import csv
import json
from pathlib import Path


GOLD_COLUMNS = [
  "trace_id",
  "task_id",
  "seed",
  "t_star",
  "annotator_a",
  "annotator_b",
  "adjudicated_label",
  "secondary_modes",
  "propagated",
  "notes",
  "judge_label",
]


def load_gold_jsonl(path: Path) -> list[dict]:
  rows = []
  with path.open(encoding="utf-8") as f:
    for line in f:
      if line.strip():
        rows.append(json.loads(line))
  return rows


def write_labeling_template(path: Path, trace_ids: list[str]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=GOLD_COLUMNS)
    writer.writeheader()
    for tid in trace_ids:
      writer.writerow({col: "" for col in GOLD_COLUMNS} | {"trace_id": tid})
