"""Tests for trace review packet generation."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cua_failure_analysis.review.labels import build_discovery_row, judge_modes_ordered
from cua_failure_analysis.review.packet import build_review_packet, parse_traj_steps
from cua_failure_analysis.review.selection import (
  is_confusing_episode,
  select_from_pool,
  select_paired_pilot_episodes,
)

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"
EPISODE_ID = "chrome/030eeff7-b492-4218-b312-701ec99ee0cc"
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "trace_review"
ROOT = Path(__file__).resolve().parents[1]
A3B_RUN = ROOT / "data/babel_outputs/20260626_172919_a3b_pilot_full_v4"
B7_RUN = ROOT / "data/babel_outputs/20260626_172922_7b_pilot_full_v4"


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
  members = json.loads((FIXTURES / "zip_members_sample.json").read_text())
  traj_src = FIXTURES / "traj_failed.jsonl"
  zip_path = tmp_path / "sample.zip"
  with zipfile.ZipFile(zip_path, "w") as zf:
    zf.writestr(f"{EPISODE_ID}/traj.jsonl", traj_src.read_bytes())
    zf.writestr(f"{EPISODE_ID}/result.txt", b"0")
    for member in members:
      if member.endswith(".png"):
        zf.writestr(f"{EPISODE_ID}/{Path(member).name}", b"\x89PNG\r\n\x1a\n")
      elif member.endswith("recording.mp4"):
        zf.writestr(f"{EPISODE_ID}/recording.mp4", b"\x00\x00\x00\x18ftypmp42")
  return zip_path


def test_parse_traj_steps():
  steps = parse_traj_steps(FIXTURES / "traj_failed.jsonl")
  assert len(steps) >= 3
  assert "freeze" in steps[0].thought.lower()


def test_judge_modes_ordered():
  modes = judge_modes_ordered(
    {"provisional_primary": "Reasoning Drift", "secondary_modes": ["Goal Hallucination"]}
  )
  assert modes == ["Reasoning Drift", "Goal Hallucination"]


def test_select_paired_pilot_episodes():
  if not A3B_RUN.exists() or not B7_RUN.exists():
    pytest.skip("v4 pilot runs not synced locally")
  episodes, groups = select_paired_pilot_episodes(
    [A3B_RUN, B7_RUN],
    tasks_file=ROOT / "config/stratified_tasks.json",
    phase="pilot",
  )
  assert len(groups) == 30
  assert len(episodes) == 60
  task_ids = {ep["task_id"] for ep in episodes}
  assert len(task_ids) == 30
  assert sum(1 for ep in episodes if ep["model"] == "a3b") == 30
  assert sum(1 for ep in episodes if ep["model"] == "7b") == 30


def test_build_review_packet(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  manifest_path = tmp_path / "manifest.json"
  manifest_path.write_text(
    json.dumps(
      {
        "packet_id": "test_packet",
        "task_groups": [],
        "episodes": [
          {
            "model": "a3b",
            "episode_id": EPISODE_ID,
            "domain": "chrome",
            "task_id": "030eeff7-b492-4218-b312-701ec99ee0cc",
            "t_star": 2,
            "provisional_primary": "Reasoning Drift",
            "secondary_modes": ["Goal Hallucination"],
            "propagated": False,
            "evidence": "judge says X",
            "confidence": 0.7,
            "run_dir": str(tmp_path),
          }
        ],
      }
    ),
    encoding="utf-8",
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )
  index = (out / "index.html").read_text(encoding="utf-8")
  episode = (out / "a3b" / EPISODE_ID.replace("/", "__") / "episode.html").read_text(
    encoding="utf-8"
  )
  assert (out / "review.js").exists()
  assert (out / "review.css").exists()
  assert (out / "human_labels.json").exists()
  assert "test_packet" in index
  assert "Judge reasoning" in episode
  assert "Reasoning Drift" in episode and "Goal Hallucination" in episode
  assert "human-reasoning" in episode
  assert "pipeline t*" in episode
  assert "judge says X" in episode


def test_build_discovery_row_merges_human():
  ep = {
    "model": "a3b",
    "episode_id": "chrome/uuid",
    "task_id": "uuid",
    "provisional_primary": "Reasoning Drift",
    "secondary_modes": [],
    "t_star": 5,
    "evidence": "judge note",
    "confidence": 0.6,
  }
  human = {
    "modes_ordered": ["Click Region Error", "Reasoning Drift"],
    "reasoning": "human note",
    "confidence": 0.9,
    "root_step": 3,
  }
  row = build_discovery_row(ep, human, columns=["judge_modes_ordered", "human_modes_ordered", "human_reasoning", "root_step"])
  assert row["judge_modes_ordered"] == "Reasoning Drift"
  assert row["human_modes_ordered"] == "Click Region Error;Reasoning Drift"
  assert row["human_reasoning"] == "human note"
  assert row["root_step"] == "3"
