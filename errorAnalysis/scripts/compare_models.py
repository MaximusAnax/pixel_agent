#!/usr/bin/env python3
"""Cross-model failure-prevalence comparison from per-run analysis outputs.

Given two or more analysis run directories (one per model, produced by
``hf_osworld_analyze.py``), build a side-by-side comparison:

- per-model failure rate over the shared task set (denominator from manifests);
- per-leaf prevalence at t* with Wilson CIs for each model;
- Perception (6 leaves) vs Cognitive (10 leaves) aggregate split per model;
- propagation rate for consequence leaves;
- co-occurrence (primary x secondary) per model;
- pilot task overlap (which tasks each model failed on + intersection).

Prevalence is conditional on failure, and failure sets differ per model, so the
report surfaces n_failed / failure_rate / task overlap and is labeled provisional
until human gold calibration (Phase D). Does not modify the taxonomy.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from cua_failure_analysis.stats.prevalence import prevalence_table, wilson_ci
from cua_failure_analysis.taxonomy import (
  COGNITIVE_LEAVES,
  PERCEPTION_LEAVES,
  FailureLeaf,
)

ROOT = Path(__file__).resolve().parents[1]
CONSEQUENCE_LEAVES = [
  FailureLeaf.ACTION_LOOPING.value,
  FailureLeaf.LONG_HORIZON_MEMORY.value,
]
PERCEPTION_VALUES = {leaf.value for leaf in PERCEPTION_LEAVES}
COGNITIVE_VALUES = {leaf.value for leaf in COGNITIVE_LEAVES}


def _read_jsonl(path: Path) -> list[dict]:
  rows: list[dict] = []
  if not path.exists():
    return rows
  with path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        rows.append(json.loads(line))
  return rows


def short_model_label(model_id: str, fallback: str) -> str:
  """Turn 'opencua-7b-cot-l2-action-history-3image-' into 'opencua-7b'."""
  if not model_id:
    return fallback
  marker = "-cot"
  if marker in model_id:
    return model_id.split(marker, 1)[0]
  return model_id.rstrip("-") or fallback


def _task_id(episode_id: str) -> str:
  return episode_id.split("/", 1)[1] if "/" in episode_id else episode_id


def load_run(run_dir: Path) -> dict:
  meta_path = run_dir / "run_metadata.json"
  meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
  label = short_model_label(meta.get("model_id", ""), run_dir.name)

  manifests = json.loads((run_dir / "episode_manifests.json").read_text(encoding="utf-8")) \
    if (run_dir / "episode_manifests.json").exists() else []
  # Manifests include all normalized episodes (successes too, even under
  # --failed-only), so they give the failure-rate denominator.
  n_episodes = len(manifests)
  failed_task_ids = {m.get("task_id") for m in manifests if m.get("success") is False}
  n_failed_manifest = len(failed_task_ids)

  labels = [
    r for r in _read_jsonl(run_dir / "failure_labels.jsonl")
    if r.get("status") == "failed" and r.get("primary_mode")
  ]

  return {
    "run_dir": str(run_dir),
    "model_label": label,
    "model_id": meta.get("model_id", ""),
    "package": meta.get("package", ""),
    "n_episodes": n_episodes,
    "n_failed": n_failed_manifest if manifests else len(labels),
    "failure_rate": (n_failed_manifest / n_episodes) if n_episodes else 0.0,
    "failed_task_ids": sorted(t for t in failed_task_ids if t),
    "labels": labels,
  }


def perception_vs_cognitive(labels: list[dict]) -> dict:
  n = len(labels)
  perc = sum(1 for r in labels if r["primary_mode"] in PERCEPTION_VALUES)
  cogn = sum(1 for r in labels if r["primary_mode"] in COGNITIVE_VALUES)
  other = n - perc - cogn
  p_lo, p_hi = wilson_ci(perc, n)
  c_lo, c_hi = wilson_ci(cogn, n)
  return {
    "n_failures": n,
    "perception": {"count": perc, "prevalence": perc / n if n else 0.0,
                   "ci_low": p_lo, "ci_high": p_hi},
    "cognitive": {"count": cogn, "prevalence": cogn / n if n else 0.0,
                  "ci_low": c_lo, "ci_high": c_hi},
    "other_unresolved": other,
  }


def propagation_rates(labels: list[dict]) -> dict:
  out = {}
  for leaf in CONSEQUENCE_LEAVES:
    leaf_rows = [r for r in labels if r["primary_mode"] == leaf]
    n = len(leaf_rows)
    prop = sum(1 for r in leaf_rows if r.get("propagated"))
    lo, hi = wilson_ci(prop, n)
    out[leaf] = {"n": n, "propagated": prop,
                 "rate": prop / n if n else 0.0, "ci_low": lo, "ci_high": hi}
  return out


def cooccurrence(labels: list[dict]) -> dict:
  matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
  for row in labels:
    for secondary in row.get("secondary_modes", []) or []:
      matrix[row["primary_mode"]][secondary] += 1
  return {k: dict(v) for k, v in matrix.items()}


def build_comparison(run_dirs: list[Path]) -> dict:
  runs = [load_run(d) for d in run_dirs]
  per_model = {}
  for run in runs:
    labels = run["labels"]
    per_model[run["model_label"]] = {
      "run_dir": run["run_dir"],
      "model_id": run["model_id"],
      "package": run["package"],
      "n_episodes": run["n_episodes"],
      "n_failed": run["n_failed"],
      "failure_rate": run["failure_rate"],
      "prevalence_table": prevalence_table(labels),
      "perception_vs_cognitive": perception_vs_cognitive(labels),
      "propagation": propagation_rates(labels),
      "cooccurrence": cooccurrence(labels),
      "tier_used_counts": dict(Counter(r.get("tier_used", "") for r in labels)),
    }

  failure_sets = {r["model_label"]: set(r["failed_task_ids"]) for r in runs}
  intersection = set.intersection(*failure_sets.values()) if failure_sets else set()
  union = set.union(*failure_sets.values()) if failure_sets else set()

  return {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "provisional": True,
    "note": (
      "Prevalence is conditional on failure; failure sets differ per model. "
      "Denominators (n_failed) and task overlap are reported. All labels are "
      "provisional until human gold calibration (Phase D)."
    ),
    "models": [r["model_label"] for r in runs],
    "per_model": per_model,
    "pilot_task_overlap": {
      "per_model_failed_task_ids": {k: sorted(v) for k, v in failure_sets.items()},
      "intersection": sorted(intersection),
      "union": sorted(union),
      "n_intersection": len(intersection),
      "n_union": len(union),
    },
  }


def _fmt_pct(x: float) -> str:
  return f"{100 * x:.0f}%"


def render_markdown(comp: dict) -> str:
  models = comp["models"]
  lines = ["# Multi-Model Failure Prevalence Comparison", ""]
  lines.append(f"- Generated: {comp['generated_at']}")
  lines.append(f"- Models: {', '.join(models)}")
  lines.append("- Status: provisional (pre human-gold calibration)")
  lines.append("")

  # Failure rate / denominators.
  lines.append("## Failure rate (over analyzed pilot episodes)")
  lines.append("")
  lines.append("| Model | Episodes | Failed | Failure rate |")
  lines.append("|---|---:|---:|---:|")
  for m in models:
    d = comp["per_model"][m]
    lines.append(f"| {m} | {d['n_episodes']} | {d['n_failed']} | {_fmt_pct(d['failure_rate'])} |")
  lines.append("")

  # Perception vs cognitive.
  lines.append("## Perception vs Cognitive (share of failures at t*)")
  lines.append("")
  lines.append("| Model | n failures | Perception | Cognitive | Other/Unresolved |")
  lines.append("|---|---:|---:|---:|---:|")
  for m in models:
    pvc = comp["per_model"][m]["perception_vs_cognitive"]
    lines.append(
      f"| {m} | {pvc['n_failures']} | "
      f"{_fmt_pct(pvc['perception']['prevalence'])} | "
      f"{_fmt_pct(pvc['cognitive']['prevalence'])} | "
      f"{pvc['other_unresolved']} |"
    )
  lines.append("")

  # Per-leaf prevalence side by side (prevalence with CI).
  lines.append("## Per-leaf prevalence at t* (conditional on failure)")
  lines.append("")
  header = "| Leaf | " + " | ".join(f"{m} (CI)" for m in models) + " |"
  sep = "|---|" + "|".join(["---"] * len(models)) + "|"
  lines.append(header)
  lines.append(sep)
  prevalence_by_model = {
    m: {row["leaf"]: row for row in comp["per_model"][m]["prevalence_table"]}
    for m in models
  }
  all_leaves = sorted({row["leaf"] for m in models for row in comp["per_model"][m]["prevalence_table"]})
  for leaf in all_leaves:
    cells = []
    any_nonzero = False
    for m in models:
      row = prevalence_by_model[m].get(leaf)
      if row and row["count"]:
        any_nonzero = True
        cells.append(
          f"{row['count']}/{row['n_failures']} {_fmt_pct(row['prevalence'])} "
          f"[{_fmt_pct(row['ci_low'])}, {_fmt_pct(row['ci_high'])}]"
        )
      else:
        cells.append("0")
    if any_nonzero:
      lines.append(f"| {leaf} | " + " | ".join(cells) + " |")
  lines.append("")

  # Propagation.
  lines.append("## Propagation rate (consequence leaves)")
  lines.append("")
  lines.append("| Model | Leaf | n | Propagated | Rate |")
  lines.append("|---|---|---:|---:|---:|")
  for m in models:
    for leaf, p in comp["per_model"][m]["propagation"].items():
      lines.append(f"| {m} | {leaf} | {p['n']} | {p['propagated']} | {_fmt_pct(p['rate'])} |")
  lines.append("")

  # Task overlap.
  ov = comp["pilot_task_overlap"]
  lines.append("## Pilot task overlap (failed task IDs)")
  lines.append("")
  lines.append(f"- Intersection (failed by all models): {ov['n_intersection']}")
  lines.append(f"- Union (failed by any model): {ov['n_union']}")
  lines.append("")
  lines.append(
    "> Denominators differ per model because each model fails on a different "
    "subset of tasks. Compare prevalence shares, not raw counts."
  )
  lines.append("")
  return "\n".join(lines) + "\n"


def main() -> None:
  p = argparse.ArgumentParser(description="Cross-model failure-prevalence comparison")
  p.add_argument("--runs", type=Path, nargs="+", required=True, help="Run dirs, one per model")
  p.add_argument("--output-dir", type=Path, default=None,
                 help="Defaults to data/comparisons/<timestamp>/")
  args = p.parse_args()

  if len(args.runs) < 2:
    p.error("Provide at least two run dirs to compare.")

  comp = build_comparison(args.runs)
  out_dir = args.output_dir or (
    ROOT / "data" / "comparisons" / datetime.now().strftime("%Y%m%d_%H%M%S")
  )
  out_dir.mkdir(parents=True, exist_ok=True)
  (out_dir / "comparison.json").write_text(json.dumps(comp, indent=2), encoding="utf-8")
  (out_dir / "comparison.md").write_text(render_markdown(comp), encoding="utf-8")

  print(f"Wrote comparison to {out_dir}")
  for m in comp["models"]:
    d = comp["per_model"][m]
    pvc = d["perception_vs_cognitive"]
    print(
      f"  {m}: failure_rate={_fmt_pct(d['failure_rate'])} "
      f"n_failed={d['n_failed']} "
      f"perception={_fmt_pct(pvc['perception']['prevalence'])} "
      f"cognitive={_fmt_pct(pvc['cognitive']['prevalence'])}"
    )


if __name__ == "__main__":
  main()
