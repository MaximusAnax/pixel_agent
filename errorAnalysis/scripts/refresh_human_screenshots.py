#!/usr/bin/env python3
"""Re-render human (guided replay) screenshots in an existing packet.

``refresh_review_packet_html.py`` only re-renders HTML from assets already on
disk, so a packet built before crosshairs existed keeps its unmarked JPEGs.
This walks the packet's human episodes, redraws each step's before-shot with the
grounded pixel crosshaired, and refreshes ``human_steps.json`` (replay status +
log tail) from the gold run dir. Run ``refresh_review_packet_html.py``
afterwards to pick the new fields up in the HTML.
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cua_failure_analysis.review.packet import (  # noqa: E402
  build_human_episode_assets,
  build_human_stub_assets,
  episode_slug,
)


def _rebuild_one(job: tuple[str, str, str]) -> str | None:
  """Re-render one episode. Runs in a worker: JPEG encode is CPU-bound and the
  packet usually lives on NFS, so a serial pass is dominated by write latency."""
  gold_dir_s, episode_dir_s, episode_id = job
  gold_dir, episode_dir = Path(gold_dir_s), Path(episode_dir_s)
  try:
    if (gold_dir / "trace.jsonl").exists():
      build_human_episode_assets(
        gold_dir, episode_dir, episode_id=episode_id, overwrite_shots=True
      )
    else:
      build_human_stub_assets(gold_dir, episode_dir, episode_id=episode_id)
  except Exception as exc:  # noqa: BLE001 - one bad replay must not kill the pass
    return f"{episode_id}: {type(exc).__name__}: {exc}"
  return None


def main() -> int:
  p = argparse.ArgumentParser(description="Redraw human replay screenshots with crosshairs")
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument(
    "--limit", type=int, default=0, help="Only process the first N human episodes (smoke test)"
  )
  p.add_argument("--jobs", type=int, default=8, help="Parallel workers (default 8)")
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  manifest_path = packet_dir / "packet_manifest.json"
  if not manifest_path.exists():
    raise SystemExit(f"No packet_manifest.json in {packet_dir}")

  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  human_eps = [ep for ep in manifest.get("episodes", []) if ep.get("model") == "human"]
  if args.limit:
    human_eps = human_eps[: args.limit]

  jobs: list[tuple[str, str, str]] = []
  skipped = 0
  for ep in human_eps:
    gold_dir = Path(str(ep.get("gold_dir") or ""))
    if not gold_dir.is_dir():
      skipped += 1
      continue
    episode_dir = packet_dir / "human" / episode_slug(ep["episode_id"])
    jobs.append((str(gold_dir), str(episode_dir), ep["episode_id"]))

  done = 0
  errors: list[str] = []
  with Pool(max(1, args.jobs)) as pool:
    for err in pool.imap_unordered(_rebuild_one, jobs):
      done += 1
      if err:
        errors.append(err)
      if done % 25 == 0:
        print(f"  {done}/{len(jobs)}…", file=sys.stderr)

  print(f"Re-rendered {done - len(errors)} human episodes ({skipped} skipped: gold dir missing)")
  for err in errors:
    print(f"  ! {err}", file=sys.stderr)
  print(f"Now run: scripts/refresh_review_packet_html.py {args.packet_id}")
  return 1 if errors else 0


if __name__ == "__main__":
  raise SystemExit(main())
