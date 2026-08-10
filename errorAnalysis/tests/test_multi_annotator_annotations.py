"""Tests for multi-annotator annotations and agreement reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cua_failure_analysis.review.annotations import (
  ANNOTATIONS_FILENAME,
  SCHEMA_VERSION,
  empty_annotations,
  get_annotator_labels,
  get_replay_audit,
  merge_annotations,
  load_annotations,
  migrate_v1_to_v2,
  replay_audit_summary,
  save_annotator_labels,
  save_replay_audit,
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
  assert data["schema_version"] == SCHEMA_VERSION
  assert set(data["annotators"]) == {"abdoul", "raghav"}
  assert data["annotators"]["abdoul"]["replay_audit"] == {}


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


def test_v2_annotations_load_as_current_schema(tmp_path: Path):
  """A pre-replay-audit file must keep its labels and gain an empty audit block."""
  path = tmp_path / ANNOTATIONS_FILENAME
  path.write_text(
    json.dumps(
      {
        "schema_version": 2,
        "packet_id": "p",
        "annotators": {
          "abdoul": {"labels": {EPISODE_KEY: {"modes_ordered": ["Reasoning Drift"]}}},
          "raghav": {"labels": {}},
        },
      }
    ),
    encoding="utf-8",
  )
  data = load_annotations(path, packet_id="p")
  assert get_annotator_labels(data, "abdoul")[EPISODE_KEY]["modes_ordered"] == ["Reasoning Drift"]
  assert get_replay_audit(data, "abdoul") == {}


def test_replay_audit_is_per_annotator_and_separate_from_labels(tmp_path: Path):
  path = tmp_path / ANNOTATIONS_FILENAME
  save_single_episode(path, "raghav", EPISODE_KEY, {"modes_ordered": ["Reasoning Drift"]}, packet_id="p")
  save_replay_audit(path, "raghav", "uuid", {"category": "ui-drift", "note": "menu moved"}, packet_id="p")
  save_replay_audit(path, "abdoul", "uuid", {"category": "timeout", "note": ""}, packet_id="p")

  data = load_annotations(path, packet_id="p")
  assert get_replay_audit(data, "raghav")["uuid"]["category"] == "ui-drift"
  assert get_replay_audit(data, "abdoul")["uuid"]["category"] == "timeout"
  # Audit notes must not leak into the taxonomy labels the agreement report reads.
  assert list(get_annotator_labels(data, "raghav")) == [EPISODE_KEY]
  assert get_annotator_labels(data, "abdoul") == {}
  assert replay_audit_summary(data)["raghav"] == {"uuid": "ui-drift"}


def test_replay_audit_rejects_unknown_category(tmp_path: Path):
  path = tmp_path / ANNOTATIONS_FILENAME
  with pytest.raises(ValueError, match="Unknown replay audit category"):
    save_replay_audit(path, "raghav", "uuid", {"category": "Reasoning Drift"}, packet_id="p")


def test_replay_audit_clears_on_empty_entry(tmp_path: Path):
  path = tmp_path / ANNOTATIONS_FILENAME
  save_replay_audit(path, "raghav", "uuid", {"category": "infra", "note": "n"}, packet_id="p")
  save_replay_audit(path, "raghav", "uuid", {"category": "", "note": ""}, packet_id="p")
  assert get_replay_audit(load_annotations(path, packet_id="p"), "raghav") == {}


def test_merge_annotations_merges_replay_audit():
  a = empty_annotations("p")
  b = empty_annotations("p")
  a["annotators"]["raghav"]["replay_audit"] = {
    "t1": {"category": "ui-drift", "updated_at": "2026-07-16T10:00:00+00:00"},
    "t2": {"category": "infra", "updated_at": "2026-07-16T09:00:00+00:00"},
  }
  b["annotators"]["raghav"]["replay_audit"] = {
    "t1": {"category": "grounding-miss", "updated_at": "2026-07-17T10:00:00+00:00"},
  }
  merged = merge_annotations(a, b)
  audit = merged["annotators"]["raghav"]["replay_audit"]
  assert audit["t1"]["category"] == "grounding-miss"
  assert audit["t2"]["category"] == "infra"


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
