"""Inter-rater agreement for human gold labels."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class AgreementReport:
  n: int
  observed_agreement: float
  cohens_kappa: float
  per_category_counts: dict[str, int]


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
  label_key: str = "primary_mode",
) -> dict[str, float]:
  """Compute kappa per leaf using one-vs-rest binary labels."""
  leaves = sorted({r[label_key] for r in records if label_key in r})
  kappas: dict[str, float] = {}
  for leaf in leaves:
    a = ["yes" if r.get(annotator_a) == leaf else "no" for r in records]
    b = ["yes" if r.get(annotator_b) == leaf else "no" for r in records]
    kappas[leaf] = cohens_kappa(a, b)
  return kappas


def judge_vs_human_agreement(
  gold: list[dict],
  judge_key: str = "judge_label",
  human_key: str = "adjudicated_label",
) -> AgreementReport:
  ha = [g[human_key] for g in gold]
  hj = [g[judge_key] for g in gold]
  agree = sum(1 for a, b in zip(ha, hj) if a == b) / len(gold)
  return AgreementReport(
    n=len(gold),
    observed_agreement=agree,
    cohens_kappa=cohens_kappa(ha, hj),
    per_category_counts=dict(Counter(ha)),
  )
