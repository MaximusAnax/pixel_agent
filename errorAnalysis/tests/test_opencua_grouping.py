"""Tests for OpenCUA episode grouping."""

import json
import zipfile
from pathlib import Path

from cua_failure_analysis.adapters.grouping import (
  episode_key_from_member,
  group_opencua_episodes,
)

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"


def test_episode_key_from_member():
  assert (
    episode_key_from_member("chrome/030eeff7-b492-4218-b312-701ec99ee0cc/traj.jsonl")
    == "chrome/030eeff7-b492-4218-b312-701ec99ee0cc"
  )
  assert episode_key_from_member("args.json") is None
  assert episode_key_from_member("chrome/traj.jsonl") is None


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
