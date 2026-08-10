"""Tests for agreement metrics (multi-label, all-applicable policy)."""

from cua_failure_analysis.labeling.agreement import (
  cohens_kappa,
  jaccard,
  judge_vs_human_agreement,
  per_leaf_kappa,
)


def test_cohens_kappa_perfect():
  labels = ["A", "B", "A", "B"]
  assert cohens_kappa(labels, labels) == 1.0


def test_judge_vs_human_singleton_backcompat():
  """Old-style single-string labels keep their pre-migration semantics."""
  gold = [
    {"adjudicated_label": "A", "judge_label": "A"},
    {"adjudicated_label": "B", "judge_label": "A"},
  ]
  report = judge_vs_human_agreement(gold)
  assert report.n == 2
  assert report.observed_agreement == 0.5


def test_jaccard():
  assert jaccard(["A", "B"], ["A", "B"]) == 1.0
  assert jaccard(["A", "B"], ["A"]) == 0.5
  assert jaccard([], []) == 1.0
  assert jaccard(["A"], ["B"]) == 0.0
  # Bare strings behave as singleton lists.
  assert jaccard("A", ["A"]) == 1.0


def test_judge_vs_human_multilabel():
  gold = [
    {"adjudicated_label": ["A", "B"], "judge_label": ["A", "B"]},
    {"adjudicated_label": ["A"], "judge_label": ["A", "C"]},
  ]
  report = judge_vs_human_agreement(gold)
  assert report.n == 2
  assert report.observed_agreement == 0.5  # only the first record set-matches
  assert report.mean_jaccard == 0.75  # (1.0 + 0.5) / 2
  # Leaf A: present for both raters in both records -> perfect agreement.
  assert report.per_leaf_kappa["A"] == 1.0
  # Leaf C: judge-only in record 2 -> disagreement.
  assert report.per_leaf_kappa["C"] < 1.0
  assert report.per_category_counts == {"A": 2, "B": 1}


def test_per_leaf_kappa_multilabel_membership():
  """Regression: kappa must use set membership, not whole-label equality.

  Under the old equality comparison, annotators who agree on leaf presence but
  order their lists differently would spuriously disagree on every leaf.
  """
  records = [
    {"annotator_a": ["A", "B"], "annotator_b": ["B", "A"]},
    {"annotator_a": ["A"], "annotator_b": ["A"]},
    {"annotator_a": ["B"], "annotator_b": ["A", "B"]},
  ]
  kappas = per_leaf_kappa(records)
  # A: a={y,y,n} b={y,y,y} -> one disagreement; B: a={y,n,y} b={y,n,y} -> perfect.
  assert kappas["B"] == 1.0
  assert kappas["A"] < 1.0


def test_per_leaf_kappa_string_backcompat():
  records = [
    {"annotator_a": "A", "annotator_b": "A"},
    {"annotator_a": "B", "annotator_b": "B"},
  ]
  kappas = per_leaf_kappa(records)
  assert kappas == {"A": 1.0, "B": 1.0}


def test_judge_vs_human_empty():
  report = judge_vs_human_agreement([])
  assert report.n == 0
