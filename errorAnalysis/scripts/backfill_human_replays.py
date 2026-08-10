#!/usr/bin/env python3
"""Extend an existing packet manifest to cover every guided replay.

Packets built before replay-status support only carry ``human`` rows for
replays that produced a ``trace.jsonl``. This adds the rest — replays killed
before writing one, and replays whose task never appeared in the HF zips — and
stamps ``replay_status`` on the rows that already exist.

It rewrites only the manifest, so it needs the gold root but not the zips (the
model episodes and their assets are left exactly as they are). Run
``refresh_human_screenshots.py`` then ``refresh_review_packet_html.py``
afterwards to build assets for the new rows and re-render the HTML.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cua_failure_analysis.review.packet import (  # noqa: E402
  REPLAY_FAILED,
  REPLAY_GOLD,
  REPLAY_INCOMPLETE,
)
from cua_failure_analysis.review.selection import load_task_domains  # noqa: E402

MODEL_ORDER = ("a3b", "7b")


def _replay_status(gold_dir: Path) -> tuple[str, dict]:
  if not (gold_dir / "trace.jsonl").exists():
    return REPLAY_INCOMPLETE, {}
  manifest_path = gold_dir / "manifest.json"
  manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
  return (REPLAY_GOLD if manifest.get("success") else REPLAY_FAILED), manifest


def main() -> int:
  p = argparse.ArgumentParser(description="Backfill human replay rows in a packet manifest")
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument("--gold-root", type=Path, required=True, help="gold/<task_id>/ replay root")
  p.add_argument("--task-list", type=Path, default=None, help="domain/task_id per line")
  p.add_argument("--dry-run", action="store_true")
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  manifest_path = packet_dir / "packet_manifest.json"
  if not manifest_path.exists():
    raise SystemExit(f"No packet_manifest.json in {packet_dir}")

  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  episodes = manifest.get("episodes", [])
  groups = {g["task_id"]: g for g in manifest.get("task_groups", [])}
  task_domains = load_task_domains(args.task_list) if args.task_list else {}

  by_task: dict[str, dict[str, dict]] = {}
  for ep in episodes:
    by_task.setdefault(ep["task_id"], {})[ep["model"]] = ep

  gold_dirs = {d.name: d for d in sorted(args.gold_root.iterdir()) if d.is_dir()}
  domains = {tid: g["domain"] for tid, g in groups.items()}
  for task_id in gold_dirs:
    domains.setdefault(task_id, task_domains.get(task_id, "unknown"))

  added_rows = added_tasks = stamped = 0
  for task_id, gold_dir in gold_dirs.items():
    status, gold_manifest = _replay_status(gold_dir)
    domain = domains[task_id]
    human_eid = f"{domain}/{task_id}"
    href = f"human/{human_eid.replace('/', '__')}/episode.html"
    models = by_task.setdefault(task_id, {})

    human = models.get("human")
    if human is None:
      human = {
        "model": "human",
        "episode_id": human_eid,
        "domain": domain,
        "task_id": task_id,
        "success": gold_manifest.get("success"),
        "t_star": None,
        "provisional_primary": "",
        "secondary_modes": [],
        "propagated": False,
        "evidence": "",
        "confidence": None,
        "tier_used": "",
        "run_dir": str(gold_dir),
        "gold_dir": str(gold_dir),
        "confusing": False,
        "instruction": gold_manifest.get("instruction", ""),
        "episode_html": href,
      }
      models["human"] = human
      added_rows += 1
    human["replay_status"] = status
    stamped += 1

    # Cross-links: models gain a human sibling, and vice versa.
    hrefs = {m: ep.get("episode_html") or "" for m, ep in models.items() if m != "human"}
    hrefs["human"] = href
    for model, ep in models.items():
      ep["siblings"] = [{"href": h, "model": m} for m, h in hrefs.items() if m != model and h]
      if not ep.get("sibling_href"):
        ep["sibling_href"] = next((h for m, h in hrefs.items() if m != model and h), "")

    group = groups.get(task_id)
    if group is None:
      group = {
        "task_id": task_id,
        "domain": domain,
        "missing_models": list(MODEL_ORDER),
        "models": {},
        "judges_disagree": False,
      }
      groups[task_id] = group
      added_tasks += 1
    group["replay_status"] = status
    group["missing_models"] = [m for m in MODEL_ORDER if m not in models]
    group["models"]["human"] = {
      "href": href,
      "episode_id": human_eid,
      "success": gold_manifest.get("success"),
      "provisional_primary": "",
      "t_star": None,
      "replay_status": status,
    }

  for task_id, group in groups.items():
    group.setdefault("replay_status", "")
    group.setdefault("domain", domains.get(task_id, "unknown"))

  # Canonical order: (domain, task_id) then a3b, 7b, human — matches selection,
  # so prev/next navigation stays coherent.
  ordered_tasks = sorted(groups, key=lambda t: (groups[t]["domain"], t))
  new_episodes = [
    by_task[task_id][model]
    for task_id in ordered_tasks
    for model in (*MODEL_ORDER, "human")
    if model in by_task.get(task_id, {})
  ]

  manifest["episodes"] = new_episodes
  manifest["task_groups"] = [groups[t] for t in ordered_tasks]
  manifest["n_episodes"] = len(new_episodes)
  manifest["n_tasks"] = len(ordered_tasks)

  print(f"human rows added: {added_rows}; task rows added: {added_tasks}; statuses set: {stamped}")
  print(f"episodes: {len(episodes)} -> {len(new_episodes)}; tasks: {len(ordered_tasks)}")
  if args.dry_run:
    print("[dry run] manifest not written")
    return 0

  backup = manifest_path.with_suffix(".json.bak")
  shutil.copy2(manifest_path, backup)
  manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
  print(f"wrote {manifest_path} (backup: {backup})")
  print(f"Next: scripts/refresh_human_screenshots.py {args.packet_id}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
