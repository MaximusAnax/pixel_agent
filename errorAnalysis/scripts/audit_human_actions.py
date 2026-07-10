#!/usr/bin/env python3
"""Audit OSWorld-Human pilot actions into deterministic / semi / grounded tiers.

Run before Human Agent batch to estimate frontier VLM grounding cost.

Usage (from errorAnalysis/):
  python scripts/audit_human_actions.py
  python scripts/audit_human_actions.py --json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

from cua_failure_analysis.oracle.action_parser import ActionTier, parse_human_action

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DEFAULT_SOURCES = CONFIG / "osworld_sources.yaml"

# Rough Sonnet multimodal cost estimate for grounding one NL click (screenshot + reply).
DEFAULT_COST_PER_GROUNDED = 0.02


def audit(pin_dir: Path, *, cost_per_grounded: float) -> dict:
  human_root = pin_dir / "human"
  if not human_root.exists():
    raise SystemExit(f"Missing {human_root}; run vendor_osworld_metadata.py first")

  tier_counts: Counter[str] = Counter()
  kind_counts: Counter[str] = Counter()
  per_task: list[dict] = []
  grounded_examples: list[str] = []

  for path in sorted(human_root.glob("*/*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    hgt = data.get("human-ground-truth") or {}
    actions = list(hgt.get("single-action") or [])
    parsed = [parse_human_action(a) for a in actions]
    local = Counter(p.tier.value for p in parsed)
    for p in parsed:
      tier_counts[p.tier.value] += 1
      kind_counts[p.kind] += 1
      if p.tier == ActionTier.GROUNDED and len(grounded_examples) < 12:
        grounded_examples.append(p.raw)
    per_task.append(
      {
        "task_id": path.stem,
        "domain": path.parent.name,
        "n_actions": len(parsed),
        "tiers": dict(local),
      }
    )

  grounded = int(tier_counts.get(ActionTier.GROUNDED.value, 0))
  report = {
    "pin": pin_dir.name,
    "task_count": len(per_task),
    "tier_counts": dict(tier_counts),
    "kind_counts": dict(kind_counts),
    "grounded_action_count": grounded,
    "estimated_grounding_api_cost_usd": round(grounded * cost_per_grounded, 2),
    "cost_per_grounded_assumption_usd": cost_per_grounded,
    "grounded_examples": grounded_examples,
    "tasks": per_task,
  }
  return report


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
  parser.add_argument("--cost-per-grounded", type=float, default=DEFAULT_COST_PER_GROUNDED)
  parser.add_argument("--json", action="store_true", help="Print full JSON report")
  args = parser.parse_args()
  sources = yaml.safe_load(args.sources.read_text(encoding="utf-8"))
  pin_dir = CONFIG / "osworld" / str(sources["pin"])
  report = audit(pin_dir, cost_per_grounded=args.cost_per_grounded)
  if args.json:
    print(json.dumps(report, indent=2))
    return
  print(f"Pin: {report['pin']}")
  print(f"Tasks: {report['task_count']}")
  print(f"Tier counts: {report['tier_counts']}")
  print(f"Kind counts: {report['kind_counts']}")
  print(f"Grounded actions: {report['grounded_action_count']}")
  print(
    f"Estimated grounding API cost: ${report['estimated_grounding_api_cost_usd']} "
    f"(at ${report['cost_per_grounded_assumption_usd']}/call)"
  )
  print("Example grounded actions:")
  for ex in report["grounded_examples"][:8]:
    print(f"  - {ex}")


if __name__ == "__main__":
  main()
