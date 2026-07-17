"""Tests for multi-annotator annotations and agreement reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cua_failure_analysis.review.annotations import (
  ANNOTATIONS_FILENAME,
  empty_annotations,
  get_annotator_labels,
  merge_annotations,
  load_annotations,
  migrate_v1_to_v2,
  save_annotator_labels,
  save_single_episode,
)
from cua_failure_analysis.review.discovery import comparison_columns
from cua_failure_analysis.review.labels import build_comparison_row

EPISODE_KEY = "a3b/chrome__uuid"


@pytest.fixture
def sample_episode() -> dict:
  return {
    "model": "a3b",
    "episode_id": "chrome/uuid",
    "task_id": "uuid",
    "provisional_primary": "Reasoning Drift",
    "secondary_modes": ["Goal Hallucination"],
    "t_star": 5,
    "evidence": "judge note",
    "confidence": 0.6,
  }


def test_empty_annotations_has_both_annotators():
  data = empty_annotations("test_packet")
  assert data["schema_version"] == 2
  assert set(data["annotators"]) == {"abdoul", "raghav"}


def test_migrate_v1_to_v2():
  v1 = {
    "schema_version": 1,
    "packet_id": "p",
    "labels": {EPISODE_KEY: {"modes_ordered": ["Click Region Error"]}},
  }
  v2 = migrate_v1_to_v2(v1, "p")
  assert v2["annotators"]["abdoul"]["labels"][EPISODE_KEY]["modes_ordered"] == ["Click Region Error"]
  assert v2["annotators"]["raghav"]["labels"] == {}


def test_merge_isolation(tmp_path: Path):
  path = tmp_path / ANNOTATIONS_FILENAME
  path.write_text(json.dumps(empty_annotations("p")), encoding="utf-8")

  save_single_episode(
    path,
    "abdoul",
    EPISODE_KEY,
    {"modes_ordered": ["Reasoning Drift"], "root_step": 3},
    packet_id="p",
  )
  save_single_episode(
    path,
    "raghav",
    EPISODE_KEY,
    {"modes_ordered": ["Goal Hallucination"], "root_step": 4},
    packet_id="p",
  )

  data = load_annotations(path, packet_id="p")
  abdoul = get_annotator_labels(data, "abdoul")[EPISODE_KEY]
  raghav = get_annotator_labels(data, "raghav")[EPISODE_KEY]
  assert abdoul["modes_ordered"] == ["Reasoning Drift"]
  assert raghav["modes_ordered"] == ["Goal Hallucination"]


def test_abdoul_bulk_save_does_not_erase_raghav(tmp_path: Path):
  path = tmp_path / ANNOTATIONS_FILENAME
  save_annotator_labels(
    path,
    "raghav",
    {EPISODE_KEY: {"modes_ordered": ["Long-Horizon Planning Error"]}},
    packet_id="p",
  )
  save_annotator_labels(
    path,
    "abdoul",
    {EPISODE_KEY: {"modes_ordered": ["Reasoning Drift"]}},
    packet_id="p",
  )

  data = load_annotations(path, packet_id="p")
  assert get_annotator_labels(data, "abdoul")[EPISODE_KEY]["modes_ordered"] == ["Reasoning Drift"]
  assert get_annotator_labels(data, "raghav")[EPISODE_KEY]["modes_ordered"] == [
    "Long-Horizon Planning Error"
  ]


def test_build_comparison_row(sample_episode: dict):
  columns = comparison_columns()
  row = build_comparison_row(
    sample_episode,
    human_a={"modes_ordered": ["Click Region Error"], "root_step": 2, "reasoning": "a"},
    human_b={"modes_ordered": ["Reasoning Drift"], "root_step": 5, "reasoning": "b"},
    annotator_a="abdoul",
    annotator_b="raghav",
    columns=columns,
  )
  assert row["judge_label"] == "Reasoning Drift"
  assert row["abdoul_primary"] == "Click Region Error"
  assert row["raghav_primary"] == "Reasoning Drift"
  assert row["abdoul_root_step"] == "2"
  assert row["raghav_root_step"] == "5"


def test_agreement_report_on_synthetic(tmp_path: Path, sample_episode: dict):
  import importlib.util

  script = Path(__file__).resolve().parents[1] / "scripts" / "report_discovery_agreement.py"
  spec = importlib.util.spec_from_file_location("report_discovery_agreement", script)
  mod = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(mod)

  manifest_path = tmp_path / "packet_manifest.json"
  manifest_path.write_text(
    json.dumps({"episodes": [sample_episode, {**sample_episode, "model": "7b"}]}),
    encoding="utf-8",
  )
  ann_path = tmp_path / ANNOTATIONS_FILENAME
  save_annotator_labels(
    ann_path,
    "abdoul",
    {
      EPISODE_KEY: {"modes_ordered": ["Reasoning Drift"]},
      "7b/chrome__uuid": {"modes_ordered": ["Reasoning Drift"]},
    },
    packet_id="p",
  )
  save_annotator_labels(
    ann_path,
    "raghav",
    {
      EPISODE_KEY: {"modes_ordered": ["Reasoning Drift"]},
      "7b/chrome__uuid": {"modes_ordered": ["Click Region Error"]},
    },
    packet_id="p",
  )

  records = mod.build_agreement_records(
    manifest_path, ann_path, annotator_a="abdoul", annotator_b="raghav"
  )
  human_human = mod.pairwise_report(records, left_key="abdoul", right_key="raghav")
  assert human_human["n"] == 2
  assert human_human["observed_agreement"] == 0.5

  judge_abdoul = mod.pairwise_report(records, left_key="judge_label", right_key="abdoul")
  assert judge_abdoul["n"] == 2
  assert judge_abdoul["observed_agreement"] == 1.0


def test_merge_annotations_newest_wins():
  a = empty_annotations("p")
  b = empty_annotations("p")
  a["annotators"]["raghav"]["labels"] = {
    "a3b/x": {"modes_ordered": ["Old"], "updated_at": "2026-07-16T10:00:00+00:00"},
    "a3b/only-a": {"modes_ordered": ["KeepA"], "updated_at": "2026-07-16T09:00:00+00:00"},
  }
  b["annotators"]["raghav"]["labels"] = {
    "a3b/x": {"modes_ordered": ["New"], "updated_at": "2026-07-17T10:00:00+00:00"},
  }
  b["annotators"]["abdoul"]["labels"] = {
    "7b/only-b": {"modes_ordered": ["KeepB"], "updated_at": "2026-07-17T08:00:00+00:00"},
  }
  merged = merge_annotations(a, b)
  raghav = merged["annotators"]["raghav"]["labels"]
  assert raghav["a3b/x"]["modes_ordered"] == ["New"]
  assert raghav["a3b/only-a"]["modes_ordered"] == ["KeepA"]
  assert merged["annotators"]["abdoul"]["labels"]["7b/only-b"]["modes_ordered"] == ["KeepB"]
