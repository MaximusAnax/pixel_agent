"""Tests for multi-label agreement metrics."""

from cua_failure_analysis.labeling.multilabel import (
  extract_modes,
  jaccard,
  judge_vs_gold_multilabel,
  multilabel_report,
  pairwise_annotator_multilabel,
)


def fs(*labels):
  return frozenset(labels)


def test_extract_modes_primary_secondary():
  rec = {"adjudicated_label": "A", "secondary_modes": ["B", "A"]}
  assert extract_modes(rec, "adjudicated_label", "secondary_modes") == fs("A", "B")


def test_extract_modes_prefers_list_key():
  rec = {"judge_modes": ["A", "B"], "judge_label": "C"}
  assert extract_modes(rec, "judge_label", None, "judge_modes") == fs("A", "B")


def test_extract_modes_unresolved_dropped():
  rec = {"judge_label": "Unresolved (missing task tag)", "judge_secondary_modes": []}
  assert extract_modes(rec, "judge_label", "judge_secondary_modes") == fs()


def test_jaccard_empty_sets_agree():
  assert jaccard(fs(), fs()) == 1.0
  assert jaccard(fs("A"), fs()) == 0.0
  assert jaccard(fs("A", "B"), fs("B", "C")) == 1 / 3


def test_multilabel_report_perfect():
  pairs = [(fs("A"), fs("A")), (fs("A", "B"), fs("A", "B"))]
  rep = multilabel_report(pairs)
  assert rep.macro_f1 == 1.0
  assert rep.exact_match_rate == 1.0
  assert rep.mean_jaccard == 1.0


def test_multilabel_report_partial():
  pairs = [
    (fs("A"), fs("A")),        # A: tp
    (fs("B"), fs("A")),        # B: fn, A: fp
  ]
  rep = multilabel_report(pairs, leaves=["A", "B"])
  a, b = rep.per_leaf["A"], rep.per_leaf["B"]
  assert (a.tp, a.fp, a.fn) == (1, 1, 0)
  assert (b.tp, b.fp, b.fn) == (0, 0, 1)
  assert rep.exact_match_rate == 0.5
  assert 0 < rep.macro_f1 < 1


def test_macro_excludes_hallucinated_leaf_micro_counts_it():
  pairs = [(fs("A"), fs("A", "Z"))]  # Z never in gold
  rep = multilabel_report(pairs)  # leaves default = gold leaves = [A]
  assert "Z" not in rep.per_leaf
  assert rep.macro_f1 == 1.0  # A perfect
  assert rep.micro_f1 < 1.0  # Z's false positive counted


def test_judge_vs_gold_multilabel_end_to_end():
  records = [
    {
      "adjudicated_label": "Action Looping (Repetition)",
      "secondary_modes": [],
      "judge_modes": ["Action Looping (Repetition)"],
    },
    {
      "adjudicated_modes": ["Click Region Error", "Action Looping (Repetition)"],
      "judge_label": "Click Region Error",
      "judge_secondary_modes": [],
    },
  ]
  rep = judge_vs_gold_multilabel(records)
  assert rep.n == 2
  assert rep.exact_match_rate == 0.5
  assert rep.per_leaf["Click Region Error"].f1 == 1.0


def test_pairwise_annotator_multilabel():
  records = [
    {"annotator_a": "A", "annotator_b": "A"},
    {"annotator_a": "A", "annotator_b": "B"},
  ]
  rep = pairwise_annotator_multilabel(records)
  assert rep.n == 2
  assert rep.exact_match_rate == 0.5
