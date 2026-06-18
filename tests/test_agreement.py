"""Tests for agreement metrics."""

from cua_failure_analysis.labeling.agreement import cohens_kappa, judge_vs_human_agreement


def test_cohens_kappa_perfect():
  labels = ["A", "B", "A", "B"]
  assert cohens_kappa(labels, labels) == 1.0


def test_judge_vs_human():
  gold = [
    {"adjudicated_label": "A", "judge_label": "A"},
    {"adjudicated_label": "B", "judge_label": "A"},
  ]
  report = judge_vs_human_agreement(gold)
  assert report.n == 2
  assert report.observed_agreement == 0.5
