"""Multi-label agreement metrics (meeting 2026-08-07, Decision 5).

The judge protocol v2 asks for ALL applicable failure modes per instance, so
agreement must be computed over label *sets*, not single labels. This module is
additive — `agreement.py` keeps the original single-label functions.

Conventions:
- An instance's label set = primary label + secondary modes, deduplicated.
- Records may carry list-valued keys (e.g. ``adjudicated_modes``) or the legacy
  primary+secondary pair; `extract_modes` handles both.
- "Unresolved" (any casing) and empty strings are treated as no-label.
"""

from __future__ import annotations

from dataclasses import dataclass, field

UNRESOLVED_PREFIX = "unresolved"


def _is_unresolved(label: str) -> bool:
  return not label or label.strip().lower().startswith(UNRESOLVED_PREFIX)


def extract_modes(
  record: dict,
  primary_key: str,
  secondary_key: str | None = None,
  list_key: str | None = None,
) -> frozenset[str]:
  """Build the label set for one rater from a record.

  Prefers ``list_key`` (new-style list of modes) when present; falls back to
  primary + secondary. Unresolved/empty labels yield an empty set.
  """
  labels: list[str] = []
  if list_key and isinstance(record.get(list_key), list):
    labels = [str(x) for x in record[list_key]]
  else:
    primary = record.get(primary_key)
    if primary is not None:
      labels.append(str(primary))
    if secondary_key and isinstance(record.get(secondary_key), list):
      labels.extend(str(x) for x in record[secondary_key])
  return frozenset(x.strip() for x in labels if not _is_unresolved(str(x)))


@dataclass
class LeafPRF:
  tp: int = 0
  fp: int = 0
  fn: int = 0

  @property
  def precision(self) -> float:
    return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

  @property
  def recall(self) -> float:
    return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

  @property
  def f1(self) -> float:
    p, r = self.precision, self.recall
    return 2 * p * r / (p + r) if (p + r) else 0.0

  def as_dict(self) -> dict:
    return {
      "tp": self.tp,
      "fp": self.fp,
      "fn": self.fn,
      "precision": round(self.precision, 4),
      "recall": round(self.recall, 4),
      "f1": round(self.f1, 4),
    }


@dataclass
class MultilabelReport:
  """Agreement between predicted label sets and gold label sets."""

  n: int
  macro_f1: float
  micro_f1: float
  exact_match_rate: float
  mean_jaccard: float
  per_leaf: dict[str, LeafPRF] = field(default_factory=dict)

  def as_dict(self) -> dict:
    return {
      "n": self.n,
      "macro_f1": round(self.macro_f1, 4),
      "micro_f1": round(self.micro_f1, 4),
      "exact_match_rate": round(self.exact_match_rate, 4),
      "mean_jaccard": round(self.mean_jaccard, 4),
      "per_leaf": {leaf: prf.as_dict() for leaf, prf in sorted(self.per_leaf.items())},
    }


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
  """Set similarity; two empty sets agree perfectly."""
  if not a and not b:
    return 1.0
  union = a | b
  return len(a & b) / len(union) if union else 1.0


def multilabel_report(
  pairs: list[tuple[frozenset[str], frozenset[str]]],
  leaves: list[str] | None = None,
) -> MultilabelReport:
  """Score (gold, predicted) label-set pairs.

  ``leaves`` fixes the macro-F1 leaf universe; defaults to every leaf seen in
  gold. Leaves that appear only in predictions still count via false positives
  on their own row when listed in ``leaves``; otherwise their false positives
  land in micro-F1 but not macro-F1 (macro over gold leaves keeps the score
  comparable when candidates hallucinate rare leaves).
  """
  if leaves is None:
    leaves = sorted({leaf for gold, _ in pairs for leaf in gold})
  per_leaf: dict[str, LeafPRF] = {leaf: LeafPRF() for leaf in leaves}
  micro = LeafPRF()
  exact = 0
  jac_total = 0.0

  for gold, pred in pairs:
    if gold == pred:
      exact += 1
    jac_total += jaccard(gold, pred)
    for leaf in gold | pred:
      in_gold, in_pred = leaf in gold, leaf in pred
      if in_gold and in_pred:
        micro.tp += 1
      elif in_pred:
        micro.fp += 1
      else:
        micro.fn += 1
      if leaf in per_leaf:
        if in_gold and in_pred:
          per_leaf[leaf].tp += 1
        elif in_pred:
          per_leaf[leaf].fp += 1
        else:
          per_leaf[leaf].fn += 1

  n = len(pairs)
  # Macro averages only leaves with support in these pairs (gold or predicted);
  # a leaf absent from both sides of every pair is undefined, not zero.
  supported = [prf for prf in per_leaf.values() if (prf.tp + prf.fp + prf.fn) > 0]
  macro = sum(prf.f1 for prf in supported) / len(supported) if supported else 0.0
  return MultilabelReport(
    n=n,
    macro_f1=macro,
    micro_f1=micro.f1,
    exact_match_rate=exact / n if n else 0.0,
    mean_jaccard=jac_total / n if n else 0.0,
    per_leaf=per_leaf,
  )


def judge_vs_gold_multilabel(
  records: list[dict],
  gold_primary_key: str = "adjudicated_label",
  gold_secondary_key: str = "secondary_modes",
  gold_list_key: str = "adjudicated_modes",
  pred_primary_key: str = "judge_label",
  pred_secondary_key: str = "judge_secondary_modes",
  pred_list_key: str = "judge_modes",
  leaves: list[str] | None = None,
) -> MultilabelReport:
  """Multi-label judge-vs-human report over gold records (both key styles)."""
  pairs = [
    (
      extract_modes(r, gold_primary_key, gold_secondary_key, gold_list_key),
      extract_modes(r, pred_primary_key, pred_secondary_key, pred_list_key),
    )
    for r in records
  ]
  return multilabel_report(pairs, leaves=leaves)


def pairwise_annotator_multilabel(
  records: list[dict],
  annotator_a_key: str = "annotator_a",
  annotator_b_key: str = "annotator_b",
  a_list_key: str = "annotator_a_modes",
  b_list_key: str = "annotator_b_modes",
  leaves: list[str] | None = None,
) -> MultilabelReport:
  """Human-human multi-label agreement (A as reference, B as prediction).

  F1 is symmetric in aggregate interpretation here: report alongside
  per-leaf kappa from `agreement.per_leaf_kappa` for the single-label view.
  """
  pairs = [
    (
      extract_modes(r, annotator_a_key, None, a_list_key),
      extract_modes(r, annotator_b_key, None, b_list_key),
    )
    for r in records
  ]
  return multilabel_report(pairs, leaves=leaves)
