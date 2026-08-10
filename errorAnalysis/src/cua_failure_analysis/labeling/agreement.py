"""Inter-rater agreement for human gold labels.

All-applicable labeling policy (ratified 2026-08-10): each rater's value per
record is an **ordered list** of taxonomy leaves, most-central-first
(``modes_ordered``). Bare strings are accepted everywhere and treated as
singleton lists, so records produced under the earlier one-primary policy keep
working and all metrics reduce to their old behavior on singleton labels.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class AgreementReport:
  n: int
  observed_agreement: float
  """Exact-set-match rate: fraction of records where both mode sets are equal."""
  cohens_kappa: float
  """Kappa over canonicalized mode *sets* (reduces to categorical kappa for singletons)."""
  per_category_counts: dict[str, int]
  """Occurrences of each leaf in the human/adjudicated labels."""
  mean_jaccard: float = 1.0
  """Mean per-record Jaccard overlap between the two mode sets."""
  per_leaf_kappa: dict[str, float] = field(default_factory=dict)
  """One-vs-rest binary kappa per leaf (presence/absence)."""


def _as_modes(value: object) -> list[str]:
  """Normalize a label value to a list of mode names."""
  if value is None:
    return []
  if isinstance(value, str):
    return [value] if value else []
  if isinstance(value, Iterable):
    return [str(v) for v in value if v]
  return [str(value)]


def _set_key(value: object) -> str:
  """Canonical string for a mode set, so kappa can treat sets as categories."""
  return "|".join(sorted(set(_as_modes(value))))


def jaccard(a: object, b: object) -> float:
  sa, sb = set(_as_modes(a)), set(_as_modes(b))
  if not sa and not sb:
    return 1.0
  return len(sa & sb) / len(sa | sb)


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
  if len(labels_a) != len(labels_b) or not labels_a:
    return 0.0
  n = len(labels_a)
  agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
  po = agree / n
  ca, cb = Counter(labels_a), Counter(labels_b)
  categories = set(ca) | set(cb)
  pe = sum((ca.get(c, 0) / n) * (cb.get(c, 0) / n) for c in categories)
  if pe == 1.0:
    return 1.0
  return (po - pe) / (1 - pe)


def per_leaf_kappa(
  records: list[dict],
  annotator_a: str = "annotator_a",
  annotator_b: str = "annotator_b",
  label_key: str | None = None,
) -> dict[str, float]:
  """One-vs-rest binary kappa per leaf, under multi-label records.

  Each record maps annotator keys to a list of modes (or a bare string).
  A leaf's binary rating per record is *presence* in that annotator's modes.
  ``label_key`` is kept for backward compatibility: when given, leaves found
  under ``record[label_key]`` are also included in the leaf universe.
  """
  leaves: set[str] = set()
  for r in records:
    leaves.update(_as_modes(r.get(annotator_a)))
    leaves.update(_as_modes(r.get(annotator_b)))
    if label_key:
      leaves.update(_as_modes(r.get(label_key)))
  kappas: dict[str, float] = {}
  for leaf in sorted(leaves):
    a = ["yes" if leaf in _as_modes(r.get(annotator_a)) else "no" for r in records]
    b = ["yes" if leaf in _as_modes(r.get(annotator_b)) else "no" for r in records]
    kappas[leaf] = cohens_kappa(a, b)
  return kappas


def judge_vs_human_agreement(
  gold: list[dict],
  judge_key: str = "judge_label",
  human_key: str = "adjudicated_label",
) -> AgreementReport:
  """Judge-vs-human agreement under all-applicable labels.

  ``observed_agreement`` is the exact-set-match rate; ``mean_jaccard`` credits
  partial overlap; ``per_leaf_kappa`` is the per-leaf presence/absence kappa
  (the primary reportable, per the protocol's per-leaf κ ≥ 0.6 target);
  ``cohens_kappa`` treats each full mode set as one category, which reduces to
  the pre-migration categorical kappa when all labels are singletons.
  """
  human = [_as_modes(g.get(human_key)) for g in gold]
  judge = [_as_modes(g.get(judge_key)) for g in gold]
  n = len(gold)
  if n == 0:
    return AgreementReport(0, 0.0, 0.0, {}, 0.0, {})
  exact = sum(1 for a, b in zip(human, judge) if set(a) == set(b)) / n
  mean_j = sum(jaccard(a, b) for a, b in zip(human, judge)) / n
  set_kappa = cohens_kappa([_set_key(a) for a in human], [_set_key(b) for b in judge])
  leaf_kappas = per_leaf_kappa(
    [{"h": a, "j": b} for a, b in zip(human, judge)],
    annotator_a="h",
    annotator_b="j",
  )
  counts = Counter(leaf for modes in human for leaf in set(modes))
  return AgreementReport(
    n=n,
    observed_agreement=exact,
    cohens_kappa=set_kappa,
    per_category_counts=dict(counts),
    mean_jaccard=mean_j,
    per_leaf_kappa=leaf_kappas,
  )
