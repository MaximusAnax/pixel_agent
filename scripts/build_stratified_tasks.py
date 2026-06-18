#!/usr/bin/env python3
"""Build pre-registered stratified 100-task list from OSWorld test_nogdrive.json."""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

OSWORLD_META_URL = (
  "https://raw.githubusercontent.com/xlang-ai/OSWorld/main/"
  "evaluation_examples/test_all_no_gdrive.json"
)
FALLBACK_URL = (
  "https://raw.githubusercontent.com/xlang-ai/OSWorld/main/"
  "evaluation_examples/test_nogdrive.json"
)

OUTPUT = Path(__file__).resolve().parents[1] / "config" / "stratified_tasks.json"
TARGET = 100
PILOT = 30

DOMAIN_TAGS = {
  "chrome": [],
  "gimp": ["fine_manipulation"],
  "libreoffice_writer": [],
  "libreoffice_calc": ["cross_app"],
  "libreoffice_impress": ["hidden_operation"],
  "thunderbird": [],
  "vlc": [],
  "vs_code": ["cross_app"],
  "os": ["infeasible"],
}


def fetch_task_meta() -> dict:
  urls = [FALLBACK_URL, OSWORLD_META_URL]
  last_err: Exception | None = None
  for url in urls:
    try:
      proc = subprocess.run(
        ["curl", "-sfL", url],
        check=True,
        capture_output=True,
        text=True,
      )
      return json.loads(proc.stdout)
    except Exception as exc:
      last_err = exc
      continue
  raise RuntimeError(f"Could not fetch OSWorld task metadata: {last_err}")


def stratify(meta: dict, target: int = TARGET) -> list[dict]:
  """meta maps domain -> list of task id strings."""
  by_domain: dict[str, list[str]] = defaultdict(list)
  for domain, ids in meta.items():
    if isinstance(ids, list):
      by_domain[domain].extend(ids)

  domains = sorted(by_domain.keys())
  per_domain = max(1, target // max(len(domains), 1))
  selected: list[dict] = []

  for domain in domains:
    ids = by_domain[domain]
    take = min(per_domain, len(ids))
    extra_tags = DOMAIN_TAGS.get(domain, [])
    for tid in ids[:take]:
      tags = list(extra_tags)
      if "multi" in tid or domain in ("libreoffice_calc", "vs_code"):
        if "cross_app" not in tags:
          tags.append("cross_app")
      selected.append(
        {
          "task_id": tid,
          "domain": domain,
          "task_tags": tags,
          "horizon": "long" if domain.startswith("libreoffice") else "medium",
        }
      )

  # Fill to target from remaining pool
  pool = []
  for domain, ids in by_domain.items():
    used = {t["task_id"] for t in selected if t["domain"] == domain}
    for tid in ids:
      if tid not in used:
        pool.append((domain, tid))
  i = 0
  while len(selected) < target and i < len(pool):
    domain, tid = pool[i]
    i += 1
    tags = list(DOMAIN_TAGS.get(domain, []))
    selected.append(
      {
        "task_id": tid,
        "domain": domain,
        "task_tags": tags,
        "horizon": "short",
      }
    )

  # Mark ~20% underspecified (deterministic: every 5th)
  for j, task in enumerate(selected):
    if j % 5 == 0:
      if "underspecified" not in task["task_tags"]:
        task["task_tags"].append("underspecified")

  return selected[:target]


def main() -> None:
  meta = fetch_task_meta()
  tasks = stratify(meta)
  pilot_ids = [t["task_id"] for t in tasks[:PILOT]]
  out = {
    "version": "1.0",
    "source": "OSWorld test_all_no_gdrive / test_nogdrive",
    "core_count": len(tasks),
    "pilot_count": PILOT,
    "seeds": [0, 1, 2],
    "pilot_task_ids": pilot_ids,
    "tasks": tasks,
  }
  OUTPUT.parent.mkdir(parents=True, exist_ok=True)
  OUTPUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
  print(f"Wrote {len(tasks)} tasks to {OUTPUT}")


if __name__ == "__main__":
  main()
