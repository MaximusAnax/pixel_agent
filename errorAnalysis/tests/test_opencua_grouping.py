"""Tests for OpenCUA episode grouping."""

import json
import zipfile
from pathlib import Path

from cua_failure_analysis.adapters.grouping import (
  detect_turns,
  episode_key_from_member,
  group_opencua_episodes,
)

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"

UUID_A = "030eeff7-b492-4218-b312-701ec99ee0cc"
UUID_B = "1334ca3e-f9e3-4db8-9ca7-b4c653be7d17"


def test_episode_key_from_member():
  assert (
    episode_key_from_member(f"chrome/{UUID_A}/traj.jsonl") == f"chrome/{UUID_A}"
  )
  assert episode_key_from_member("args.json") is None
  assert episode_key_from_member("chrome/traj.jsonl") is None


def test_episode_key_from_member_turn_prefix():
  # OpenCUA-7B-15 layout: turn_N/{domain}/{uuid}/...
  assert (
    episode_key_from_member(f"turn_2/libreoffice_calc/{UUID_B}/traj.jsonl")
    == f"libreoffice_calc/{UUID_B}"
  )
  # A turn-prefixed config file with no task uuid is ignored.
  assert episode_key_from_member("turn_2/args.json") is None


def _write_zip(tmp_path: Path, members: list[str]) -> Path:
  zip_path = tmp_path / "sample.zip"
  with zipfile.ZipFile(zip_path, "w") as zf:
    for member in members:
      zf.writestr(member, "x")
  return zip_path


def test_group_selects_single_turn_for_multi_attempt(tmp_path: Path):
  members = [
    "turn_1/args.json",
    f"turn_1/chrome/{UUID_A}/traj.jsonl",
    f"turn_1/chrome/{UUID_A}/step_1.png",
    f"turn_2/chrome/{UUID_A}/traj.jsonl",
    f"turn_3/chrome/{UUID_A}/traj.jsonl",
    f"turn_2/libreoffice_calc/{UUID_B}/traj.jsonl",
  ]
  zip_path = _write_zip(tmp_path, members)

  with zipfile.ZipFile(zip_path) as zf:
    assert detect_turns(zf) == ["turn_1", "turn_2", "turn_3"]
    bundles = group_opencua_episodes(zf, select_turn="turn_1")

  by_id = {b.episode_id: b for b in bundles}
  # Only turn_1 episodes survive: chrome task present, libreoffice (turn_2 only) dropped.
  assert set(by_id) == {f"chrome/{UUID_A}"}
  chrome = by_id[f"chrome/{UUID_A}"]
  assert chrome.task_id == UUID_A
  assert chrome.domain == "chrome"
  # No cross-turn member leakage.
  assert all(m.startswith("turn_1/") for m in chrome.members)
  assert len(chrome.members) == 2


def test_group_defaults_to_lowest_turn_when_select_absent(tmp_path: Path):
  members = [
    f"turn_2/chrome/{UUID_A}/traj.jsonl",
    f"turn_3/chrome/{UUID_A}/traj.jsonl",
  ]
  zip_path = _write_zip(tmp_path, members)
  with zipfile.ZipFile(zip_path) as zf:
    bundles = group_opencua_episodes(zf, select_turn="turn_1")
  # turn_1 absent -> fall back to lowest present (turn_2).
  assert {b.episode_id for b in bundles} == {f"chrome/{UUID_A}"}
  assert all(m.startswith("turn_2/") for b in bundles for m in b.members)


def test_group_opencua_episodes_excludes_args_json(tmp_path: Path):
  members = json.loads((FIXTURES / "zip_members_sample.json").read_text())
  zip_path = tmp_path / "sample.zip"
  with zipfile.ZipFile(zip_path, "w") as zf:
    for member in members:
      zf.writestr(member, "x")

  with zipfile.ZipFile(zip_path) as zf:
    bundles = group_opencua_episodes(zf)

  episode_ids = {b.episode_id for b in bundles}
  assert "args.json" not in episode_ids
  assert "chrome/030eeff7-b492-4218-b312-701ec99ee0cc" in episode_ids
