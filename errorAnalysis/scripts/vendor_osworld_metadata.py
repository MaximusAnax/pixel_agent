#!/usr/bin/env python3
"""Vendor OSWorld task JSONs + OSWorld-Human JSONs for the pilot (or core) set.

Fetches only small metadata files from pinned GitHub commits — never HF trajectory
zips. Writes under config/osworld/<pin>/.

Usage (from errorAnalysis/):
  python scripts/vendor_osworld_metadata.py
  python scripts/vendor_osworld_metadata.py --phase core
  python scripts/vendor_osworld_metadata.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DEFAULT_SOURCES = CONFIG / "osworld_sources.yaml"
DEFAULT_STRATIFIED = CONFIG / "stratified_tasks.json"


def _load_yaml(path: Path) -> dict:
  return yaml.safe_load(path.read_text(encoding="utf-8"))


def _raw_url(repo: str, commit: str, rel_path: str) -> str:
  return f"https://raw.githubusercontent.com/{repo}/{commit}/{rel_path}"


def _fetch(url: str, *, retries: int = 3, pause: float = 0.4) -> bytes:
  last_err: Exception | None = None
  headers = {"User-Agent": "pixelAgent-vendor/1.0"}
  for attempt in range(retries):
    try:
      with httpx.Client(timeout=60.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        if resp.status_code == 404:
          raise FileNotFoundError(f"404 for {url}")
        resp.raise_for_status()
        return resp.content
    except FileNotFoundError:
      raise
    except Exception as exc:
      last_err = exc
      time.sleep(pause * (attempt + 1))
  raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def _pilot_or_core_tasks(stratified: dict, phase: str) -> list[dict]:
  by_id = {row["task_id"]: row for row in stratified.get("tasks", [])}
  if phase == "pilot":
    ids = list(stratified["pilot_task_ids"])
  elif phase == "core":
    ids = [row["task_id"] for row in stratified.get("tasks", [])][: int(stratified.get("core_count", 100))]
  else:
    raise ValueError(f"Unknown phase: {phase}")
  rows: list[dict] = []
  missing: list[str] = []
  for tid in ids:
    row = by_id.get(tid)
    if not row:
      missing.append(tid)
      continue
    rows.append({"task_id": tid, "domain": row["domain"]})
  if missing:
    raise SystemExit(f"Task IDs missing from stratified_tasks.json: {missing}")
  return rows


def vendor(phase: str, *, dry_run: bool = False, sources_path: Path = DEFAULT_SOURCES) -> Path:
  sources = _load_yaml(sources_path)
  stratified = json.loads(DEFAULT_STRATIFIED.read_text(encoding="utf-8"))
  pin = str(sources["pin"])
  osw = sources["osworld"]
  human = sources["osworld_human"]
  tasks = _pilot_or_core_tasks(stratified, phase)

  out_root = CONFIG / "osworld" / pin
  tasks_dir = out_root / "tasks"
  human_dir = out_root / "human"
  print(f"Pin: {pin}")
  print(f"Phase: {phase} ({len(tasks)} tasks)")
  print(f"Output: {out_root}")

  if dry_run:
    for row in tasks:
      task_rel = osw["task_path_template"].format(domain=row["domain"], task_id=row["task_id"])
      human_rel = human["task_path_template"].format(domain=row["domain"], task_id=row["task_id"])
      print(f"  would fetch task  {_raw_url(osw['repo'], osw['commit'], task_rel)}")
      print(f"  would fetch human {_raw_url(human['repo'], human['commit'], human_rel)}")
    return out_root

  out_root.mkdir(parents=True, exist_ok=True)
  tasks_dir.mkdir(parents=True, exist_ok=True)
  human_dir.mkdir(parents=True, exist_ok=True)

  fetched: list[dict] = []
  errors: list[dict] = []

  for i, row in enumerate(tasks, start=1):
    domain = row["domain"]
    task_id = row["task_id"]
    task_rel = osw["task_path_template"].format(domain=domain, task_id=task_id)
    human_rel = human["task_path_template"].format(domain=domain, task_id=task_id)
    task_url = _raw_url(osw["repo"], osw["commit"], task_rel)
    human_url = _raw_url(human["repo"], human["commit"], human_rel)
    task_out = tasks_dir / domain / f"{task_id}.json"
    human_out = human_dir / domain / f"{task_id}.json"
    print(f"[{i}/{len(tasks)}] {domain}/{task_id}")
    try:
      task_bytes = _fetch(task_url)
      task_out.parent.mkdir(parents=True, exist_ok=True)
      task_out.write_bytes(task_bytes)
      # Validate JSON
      json.loads(task_bytes.decode("utf-8"))
    except Exception as exc:
      errors.append({"task_id": task_id, "domain": domain, "kind": "task", "error": str(exc)})
      print(f"  ERROR task: {exc}", file=sys.stderr)
      continue
    try:
      human_bytes = _fetch(human_url)
      human_out.parent.mkdir(parents=True, exist_ok=True)
      human_out.write_bytes(human_bytes)
      json.loads(human_bytes.decode("utf-8"))
    except Exception as exc:
      errors.append({"task_id": task_id, "domain": domain, "kind": "human", "error": str(exc)})
      print(f"  ERROR human: {exc}", file=sys.stderr)
      continue
    fetched.append(
      {
        "task_id": task_id,
        "domain": domain,
        "task_path": str(task_out.relative_to(ROOT)),
        "human_path": str(human_out.relative_to(ROOT)),
      }
    )
    time.sleep(0.15)

  manifest = {
    "pin": pin,
    "phase": phase,
    "fetched_at": datetime.now(timezone.utc).isoformat(),
    "osworld": {"repo": osw["repo"], "commit": osw["commit"]},
    "osworld_human": {"repo": human["repo"], "commit": human["commit"]},
    "task_count": len(fetched),
    "error_count": len(errors),
    "tasks": fetched,
    "errors": errors,
  }
  (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
  print(f"Wrote {len(fetched)} tasks; {len(errors)} errors → {out_root / 'manifest.json'}")
  if errors:
    print("Errors:", json.dumps(errors, indent=2), file=sys.stderr)
    raise SystemExit(1)
  return out_root


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--phase", choices=("pilot", "core"), default="pilot")
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
  args = parser.parse_args()
  vendor(args.phase, dry_run=args.dry_run, sources_path=args.sources)


if __name__ == "__main__":
  main()
