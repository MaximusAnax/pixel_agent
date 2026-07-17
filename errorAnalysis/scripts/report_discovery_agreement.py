#!/usr/bin/env python3
"""Pairwise agreement report for taxonomy discovery labels (judge + two humans)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cua_failure_analysis.labeling.agreement import cohens_kappa, judge_vs_human_agreement, per_leaf_kappa
from cua_failure_analysis.review.annotations import (
  ANNOTATIONS_FILENAME,
  REGISTERED_ANNOTATORS,
  get_annotator_labels,
  load_annotations,
  primary_mode,
)
from cua_failure_analysis.review.labels import judge_modes_ordered, label_storage_key

ROOT = Path(__file__).resolve().parents[1]


def _root_step_agreement(
  records: list[dict],
  key_a: str,
  key_b: str,
) -> dict[str, float | int]:
  pairs = [
    (r.get(key_a), r.get(key_b))
    for r in records
    if r.get(key_a) not in (None, "") and r.get(key_b) not in (None, "")
  ]
  if not pairs:
    return {"n": 0, "exact_match_rate": 0.0, "within_one_rate": 0.0}
  exact = sum(1 for a, b in pairs if str(a) == str(b))
  within_one = sum(1 for a, b in pairs if abs(int(a) - int(b)) <= 1)
  n = len(pairs)
  return {
    "n": n,
    "exact_match_rate": exact / n,
    "within_one_rate": within_one / n,
  }


def build_agreement_records(
  manifest_path: Path,
  annotations_path: Path,
  *,
  annotator_a: str,
  annotator_b: str,
) -> list[dict]:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  data = load_annotations(annotations_path, packet_dir=manifest_path.parent)
  labels_a = get_annotator_labels(data, annotator_a)
  labels_b = get_annotator_labels(data, annotator_b)

  records: list[dict] = []
  for ep in manifest.get("episodes", []):
    model = ep.get("model", "")
    episode_id = ep["episode_id"]
    key = label_storage_key(model, episode_id)
    judge_modes = judge_modes_ordered(ep)
    entry_a = labels_a.get(key)
    entry_b = labels_b.get(key)
    records.append(
      {
        "episode_key": key,
        "task_id": ep.get("task_id") or "",
        "model": model,
        "judge_label": judge_modes[0] if judge_modes else "",
        "judge_root_step": ep.get("t_star"),
        annotator_a: primary_mode(entry_a),
        annotator_b: primary_mode(entry_b),
        f"{annotator_a}_root_step": (entry_a or {}).get("root_step"),
        f"{annotator_b}_root_step": (entry_b or {}).get("root_step"),
      }
    )
  return records


def pairwise_report(
  records: list[dict],
  *,
  left_key: str,
  right_key: str,
  left_root: str | None = None,
  right_root: str | None = None,
) -> dict:
  paired = [r for r in records if r.get(left_key) and r.get(right_key)]
  if not paired:
    return {"n": 0, "observed_agreement": 0.0, "cohens_kappa": 0.0, "per_leaf_kappa": {}}

  left_labels = [r[left_key] for r in paired]
  right_labels = [r[right_key] for r in paired]
  report = judge_vs_human_agreement(
    [{"judge_label": a, "adjudicated_label": b} for a, b in zip(left_labels, right_labels)],
    judge_key="judge_label",
    human_key="adjudicated_label",
  )
  leaf_kappa = per_leaf_kappa(
    [{left_key: a, right_key: b} for a, b in zip(left_labels, right_labels)],
    annotator_a=left_key,
    annotator_b=right_key,
    label_key=left_key,
  )
  out: dict = {
    "n": report.n,
    "observed_agreement": report.observed_agreement,
    "cohens_kappa": report.cohens_kappa,
    "per_leaf_kappa": leaf_kappa,
  }
  if left_root and right_root:
    out["root_step"] = _root_step_agreement(paired, left_root, right_root)
  return out


def format_markdown(report: dict) -> str:
  lines = ["# Discovery agreement report", ""]
  for title, block in report.get("comparisons", {}).items():
    lines.append(f"## {title}")
    lines.append(f"- n (overlapping labeled): {block.get('n', 0)}")
    lines.append(f"- Observed agreement: {block.get('observed_agreement', 0):.3f}")
    lines.append(f"- Cohen's κ: {block.get('cohens_kappa', 0):.3f}")
    per_leaf = block.get("per_leaf_kappa") or {}
    if per_leaf:
      lines.append("- Per-leaf κ:")
      for leaf, kappa in sorted(per_leaf.items()):
        lines.append(f"  - {leaf}: {kappa:.3f}")
    root = block.get("root_step")
    if root and root.get("n"):
      lines.append(
        f"- Root step: exact={root['exact_match_rate']:.3f}, "
        f"within-1={root['within_one_rate']:.3f} (n={root['n']})"
      )
    lines.append("")
  return "\n".join(lines).rstrip() + "\n"


def main() -> None:
  p = argparse.ArgumentParser(description="Report judge vs human and human vs human agreement")
  p.add_argument("--manifest", type=Path, required=True)
  p.add_argument("--annotations", type=Path, default=None)
  p.add_argument("--annotator-a", default=REGISTERED_ANNOTATORS[0])
  p.add_argument("--annotator-b", default=REGISTERED_ANNOTATORS[1])
  p.add_argument(
    "--output-json",
    type=Path,
    default=ROOT / "data" / "labeling" / "discovery_agreement_report.json",
  )
  p.add_argument(
    "--output-md",
    type=Path,
    default=ROOT / "data" / "labeling" / "discovery_agreement_report.md",
  )
  args = p.parse_args()

  annotations_path = args.annotations or args.manifest.parent / ANNOTATIONS_FILENAME
  records = build_agreement_records(
    args.manifest,
    annotations_path,
    annotator_a=args.annotator_a,
    annotator_b=args.annotator_b,
  )

  comparisons = {
    f"Judge vs {args.annotator_a}": pairwise_report(
      records, left_key="judge_label", right_key=args.annotator_a
    ),
    f"Judge vs {args.annotator_b}": pairwise_report(
      records, left_key="judge_label", right_key=args.annotator_b
    ),
    f"{args.annotator_a} vs {args.annotator_b}": pairwise_report(
      records,
      left_key=args.annotator_a,
      right_key=args.annotator_b,
      left_root=f"{args.annotator_a}_root_step",
      right_root=f"{args.annotator_b}_root_step",
    ),
  }

  report = {
    "packet_id": args.manifest.parent.name,
    "manifest": str(args.manifest),
    "annotations": str(annotations_path),
    "annotator_a": args.annotator_a,
    "annotator_b": args.annotator_b,
    "comparisons": comparisons,
  }

  args.output_json.parent.mkdir(parents=True, exist_ok=True)
  args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
  args.output_md.write_text(format_markdown(report), encoding="utf-8")

  for title, block in comparisons.items():
    print(f"{title}: n={block['n']} κ={block['cohens_kappa']:.3f}")
  print(f"Wrote {args.output_json}")
  print(f"Wrote {args.output_md}")


if __name__ == "__main__":
  main()
