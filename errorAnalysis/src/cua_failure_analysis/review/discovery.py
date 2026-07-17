"""Taxonomy discovery labeling columns (Layer A — before gold-set calibration)."""

from __future__ import annotations

from cua_failure_analysis.labeling.gold_set import GOLD_COLUMNS

DISCOVERY_EXTRA_COLUMNS = [
  "model",
  "episode_id",
  "domain",
  "sibling_href",
  "reviewer",
  "root_step",
  "human_modes_ordered",
  "primary_revised",
  "secondary_revised",
  "human_reasoning",
  "human_confidence",
  "judge_t_star",
  "judge_modes_ordered",
  "judge_reasoning",
  "judge_confidence",
  "is_propagated",
  "propagated_from_step",
  "evaluator_mismatch",
  "taxonomy_issue",
  "candidate_new_leaf",
  "episode_html",
  "provisional_primary",
  "provisional_evidence",
  "tier_used",
]

DISCOVERY_COLUMNS = [
  *GOLD_COLUMNS,
  *[c for c in DISCOVERY_EXTRA_COLUMNS if c not in GOLD_COLUMNS],
]

COMPARISON_ANNOTATOR_SUFFIXES = [
  "modes_ordered",
  "primary",
  "root_step",
  "reasoning",
  "confidence",
  "is_propagated",
]


def comparison_columns(annotator_a: str = "abdoul", annotator_b: str = "raghav") -> list[str]:
  """Wide worksheet columns for judge + two annotators."""
  base = [
    "trace_id",
    "task_id",
    "model",
    "episode_id",
    "domain",
    "judge_label",
    "judge_t_star",
    "judge_modes_ordered",
    "judge_reasoning",
    "judge_confidence",
  ]
  for annotator_id in (annotator_a, annotator_b):
    for suffix in COMPARISON_ANNOTATOR_SUFFIXES:
      col = f"{annotator_id}_{suffix}"
      if col not in base:
        base.append(col)
  return base
