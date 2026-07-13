#!/usr/bin/env python3
"""Aggregate per-task gold-trajectory results into a summary.

Scans <gold_root>/<uuid>/manifest.json produced by replay_agent and reports
overall pass rate and the gold set (evaluator-verified successes).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-root", default="/data/group_data/mattlab/raghavg3/osworld_env/gold")
    ap.add_argument("--task-list", default="/data/group_data/mattlab/raghavg3/osworld_env/run/all_tasks.txt")
    ap.add_argument("--out", default="/data/group_data/mattlab/raghavg3/osworld_env/gold/summary.json")
    args = ap.parse_args()

    root = Path(args.gold_root)
    app_of = {}
    if Path(args.task_list).exists():
        for line in Path(args.task_list).read_text().splitlines():
            if "/" in line:
                app, uuid = line.split("/", 1)
                app_of[uuid] = app

    rows, gold, failed, errored, missing = [], [], [], [], []
    total = len(app_of) or None
    for d in sorted(root.glob("*/")):
        uuid = d.name
        mf = d / "manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text())
            row = {"uuid": uuid, "app": app_of.get(uuid), "success": m.get("success"),
                   "score": m.get("score"), "steps": m.get("total_steps")}
            rows.append(row)
            (gold if m.get("success") else failed).append(uuid)
        elif (d / "vm_fail.txt").exists() or (d / "replay.log").exists():
            errored.append(uuid)

    done = len(rows)
    by_app = {}
    for r in rows:
        a = r["app"] or "?"
        by_app.setdefault(a, {"done": 0, "gold": 0})
        by_app[a]["done"] += 1
        by_app[a]["gold"] += 1 if r["success"] else 0

    summary = {
        "total_tasks": total,
        "attempted": done,
        "gold_passed": len(gold),
        "failed_eval": len(failed),
        "errored_or_incomplete": len(errored),
        "pass_rate_of_attempted": round(len(gold) / done, 3) if done else None,
        "by_app": by_app,
        "gold_uuids": gold,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "gold_uuids"}, indent=2))
    print(f"\ngold set: {len(gold)} tasks -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
