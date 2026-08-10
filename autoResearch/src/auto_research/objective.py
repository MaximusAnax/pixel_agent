"""The frozen objective: agreement with gold labels on the pinned eval set.

Primary scalar = macro-F1 over taxonomy leaves, multi-label (see scoping doc
§4). Exact-match rate and Jaccard are reported as guard metrics. The eval set
is SHA-256 pinned; scoring refuses to run against a modified set.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from cua_failure_analysis.labeling.multilabel import MultilabelReport, multilabel_report

PRIMARY_METRIC = "macro_f1"


@dataclass
class EvalCase:
  case_id: str
  split: str  # "calibration" | "holdout"
  trace_path: Path
  gold_modes: frozenset[str]
  instruction: str = ""
  task_tags: list[str] = field(default_factory=list)
  reference_summary: str = ""
  osworld_score: float | None = None
  eval_output: str = ""


@dataclass
class EvalSet:
  root: Path
  cases: list[EvalCase]
  content_hash: str

  def split(self, name: str) -> list[EvalCase]:
    return [c for c in self.cases if c.split == name]


@dataclass
class SplitScores:
  report: MultilabelReport

  @property
  def primary(self) -> float:
    return getattr(self.report, PRIMARY_METRIC)

  def as_dict(self) -> dict:
    return {"primary_metric": PRIMARY_METRIC, "primary": round(self.primary, 4), **self.report.as_dict()}


@dataclass
class Scores:
  calibration: SplitScores
  holdout: SplitScores

  def as_dict(self) -> dict:
    return {"calibration": self.calibration.as_dict(), "holdout": self.holdout.as_dict()}


def _hash_eval_content(manifest: dict, root: Path) -> str:
  """Hash gold labels + trace bytes so any drift is detected."""
  h = hashlib.sha256()
  cases = sorted(manifest.get("cases", []), key=lambda c: c["case_id"])
  h.update(json.dumps(cases, sort_keys=True, separators=(",", ":")).encode())
  for case in cases:
    trace = root / case["trace"]
    if trace.exists():
      h.update(trace.read_bytes())
  return h.hexdigest()[:16]


def load_eval_set(root: Path, verify: bool = True) -> EvalSet:
  manifest_path = root / "eval_manifest.json"
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  content_hash = _hash_eval_content(manifest, root)
  if verify:
    stored = manifest.get("content_hash")
    if stored and stored != content_hash:
      raise RuntimeError(
        f"Eval set modified: manifest content_hash={stored} but computed="
        f"{content_hash}. The eval set is frozen — rebuild it deliberately "
        "with build_eval_set.py (human action), never from inside the loop."
      )
  cases = [
    EvalCase(
      case_id=c["case_id"],
      split=c["split"],
      trace_path=root / c["trace"],
      gold_modes=frozenset(c["gold_modes"]),
      instruction=c.get("instruction", ""),
      task_tags=list(c.get("task_tags", [])),
      reference_summary=c.get("reference_summary", ""),
      osworld_score=c.get("osworld_score"),
      eval_output=c.get("eval_output", ""),
    )
    for c in manifest["cases"]
  ]
  return EvalSet(root=root, cases=cases, content_hash=content_hash)


def score_predictions(
  eval_set: EvalSet, predictions: dict[str, frozenset[str]]
) -> Scores:
  """Score {case_id: predicted mode set} against gold, per split."""
  missing = [c.case_id for c in eval_set.cases if c.case_id not in predictions]
  if missing:
    raise ValueError(f"Predictions missing for cases: {missing}")

  def split_scores(split: str) -> SplitScores:
    cases = eval_set.split(split)
    pairs = [(c.gold_modes, predictions[c.case_id]) for c in cases]
    leaves = sorted({leaf for c in eval_set.cases for leaf in c.gold_modes})
    return SplitScores(report=multilabel_report(pairs, leaves=leaves))

  return Scores(calibration=split_scores("calibration"), holdout=split_scores("holdout"))
