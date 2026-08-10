#!/usr/bin/env python3
"""Provisional multimodal rejudge for the pilot (judge_context_version=osworld_v1).

HARD GATE: refuses episodes unless partner oracle_status is ready|partial.
Never overwrites prior failure_labels.jsonl — writes a versioned sibling file.

Usage (from errorAnalysis/, after partner artifacts exist):
  python scripts/estimate_judge_cost.py ...   # include human screenshot tokens
  python scripts/rejudge_pilot.py --run-dir <path> --oracle-root "$ORACLE_ROOT"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from cua_failure_analysis.attribution.pipeline import (
  attribute_run,
  load_human_reference_steps,
  resolve_oracle_dir,
)
from cua_failure_analysis.judge.anthropic_client import AnthropicJudge, AnthropicJudgeConfig

JUDGE_CONTEXT_VERSION = "osworld_v1"


def _find_traces(run_dir: Path) -> list[Path]:
  return sorted(run_dir.glob("**/trace.jsonl"))


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--run-dir", type=Path, required=True, help="Analysis run with traces/")
  parser.add_argument(
    "--oracle-root",
    type=Path,
    default=None,
    help="Root containing <domain>/<task_id>/human_traj.json (+ obs PNGs). "
    "Defaults to $ORACLE_ROOT when unset.",
  )
  parser.add_argument(
    "--output",
    type=Path,
    default=None,
    help="Output JSONL (default: run-dir/failure_labels_osworld_v1.jsonl)",
  )
  parser.add_argument(
    "--failed-only",
    action="store_true",
    default=True,
    help="Only rejudge failed episodes (default true)",
  )
  parser.add_argument("--include-success", action="store_true")
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--model", default="claude-sonnet-4-6")
  args = parser.parse_args()

  oracle_root = args.oracle_root
  if oracle_root is None:
    env_root = os.environ.get("ORACLE_ROOT", "").strip()
    oracle_root = Path(env_root) if env_root else None
  if oracle_root is None:
    raise SystemExit("Pass --oracle-root or set ORACLE_ROOT to partner artifact tree")

  failed_only = not args.include_success
  out_path = args.output or (args.run_dir / f"failure_labels_{JUDGE_CONTEXT_VERSION}.jsonl")
  traces = _find_traces(args.run_dir)
  if not traces:
    raise SystemExit(f"No trace.jsonl under {args.run_dir}")

  api_key = os.environ.get("ANTHROPIC_API_KEY", "")
  if not args.dry_run and not api_key:
    raise SystemExit("ANTHROPIC_API_KEY required (or pass --dry-run)")

  judge = None
  if not args.dry_run:
    judge = AnthropicJudge(AnthropicJudgeConfig(api_key=api_key, model=args.model))

  written = 0
  skipped = 0
  gated = 0
  records: list[dict] = []

  for trace_path in traces:
    manifest_path = trace_path.parent / "manifest.json"
    manifest = {}
    if manifest_path.exists():
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    success = bool(manifest.get("success"))
    if failed_only and success:
      skipped += 1
      continue
    task_id = str(manifest.get("task_id") or trace_path.parent.parent.name)
    domain = str(manifest.get("domain") or trace_path.parent.parent.parent.name)
    oracle_dir = resolve_oracle_dir(oracle_root, domain, task_id)
    human_steps, status = load_human_reference_steps(oracle_dir=oracle_dir)
    if status not in {"ready", "partial"}:
      gated += 1
      print(
        f"GATE skip {domain}/{task_id}: oracle_status={status or 'missing'}",
        file=sys.stderr,
      )
      continue

    if args.dry_run:
      records.append(
        {
          "trace_path": str(trace_path),
          "task_id": task_id,
          "domain": domain,
          "oracle_status": status,
          "human_steps": len(human_steps),
          "judge_context_version": JUDGE_CONTEXT_VERSION,
          "dry_run": True,
        }
      )
      written += 1
      continue

    assert judge is not None
    attr = attribute_run(
      trace_path,
      instruction=str(manifest.get("canonical_instruction") or manifest.get("instruction") or ""),
      judge=judge,
      oracle_dir=oracle_dir,
      require_oracle_for_judge=True,
    )
    records.append(
      {
        "trace_path": str(trace_path),
        "task_id": task_id,
        "domain": domain,
        "oracle_status": status,
        "judge_context_version": JUDGE_CONTEXT_VERSION,
        "rejudged_at": datetime.now(timezone.utc).isoformat(),
        **attr.model_dump(),
      }
    )
    written += 1

  out_path.parent.mkdir(parents=True, exist_ok=True)
  with out_path.open("w", encoding="utf-8") as f:
    for row in records:
      f.write(json.dumps(row) + "\n")

  print(
    f"Wrote {written} records → {out_path} "
    f"(skipped_success={skipped}, gated_no_oracle={gated}, version={JUDGE_CONTEXT_VERSION})"
  )
  if gated and written == 0:
    raise SystemExit(
      "No episodes rejudged — partner Human Agent screenshots not ready "
      "(need oracle_status ready|partial under --oracle-root)."
    )


if __name__ == "__main__":
  main()
