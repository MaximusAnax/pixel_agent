#!/usr/bin/env python3
"""Re-render review packet HTML from on-disk episode assets (no zip / Babel rebuild)."""

from __future__ import annotations

import argparse
from pathlib import Path

from cua_failure_analysis.review.packet import refresh_review_packet_html

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = ROOT / "templates" / "trace_review"


def main() -> None:
  p = argparse.ArgumentParser(
    description="Refresh episode/index HTML for an existing local review packet"
  )
  p.add_argument(
    "packet_id",
    nargs="?",
    default="pilot_taxonomy_paired_20260703",
    help="Subdir under data/review_packets/",
  )
  p.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
  p.add_argument(
    "--oracle-root",
    type=Path,
    default=None,
    help="Partner oracle artifact root (or ORACLE_ROOT env)",
  )
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  out = refresh_review_packet_html(
    packet_dir,
    template_dir=args.template_dir,
    oracle_root=args.oracle_root,
  )
  print(f"Refreshed HTML: {out / 'index.html'}")


if __name__ == "__main__":
  main()
