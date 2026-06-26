"""Tests for judge screenshot extraction from HF zips."""

import zipfile
from pathlib import Path

from cua_failure_analysis.adapters.base import EpisodeBundle
from cua_failure_analysis.adapters.screenshots import (
  extract_screenshot_for_judge,
  resolve_screenshot_member,
)
from cua_failure_analysis.trace.schema import TraceStep


def test_resolve_screenshot_member():
  bundle = EpisodeBundle(
    episode_id="chrome/030eeff7-b492-4218-b312-701ec99ee0cc",
    task_id="030eeff7-b492-4218-b312-701ec99ee0cc",
    domain="chrome",
    members=["chrome/030eeff7-b492-4218-b312-701ec99ee0cc/step_1_20250730@083931.png"],
  )
  step = TraceStep(
    task_id=bundle.task_id,
    seed=0,
    step=1,
    screenshot_path="chrome/030eeff7-b492-4218-b312-701ec99ee0cc/step_1_20250730@083931.png",
  )
  assert resolve_screenshot_member(bundle, step) == bundle.members[0]


def test_extract_screenshot_for_judge(tmp_path: Path):
  png_bytes = b"\x89PNG\r\n\x1a\n"
  member = "chrome/030eeff7-b492-4218-b312-701ec99ee0cc/step_1_20250730@083931.png"
  zip_path = tmp_path / "episode.zip"
  with zipfile.ZipFile(zip_path, "w") as zf:
    zf.writestr(member, png_bytes)

  bundle = EpisodeBundle(
    episode_id="chrome/030eeff7-b492-4218-b312-701ec99ee0cc",
    task_id="030eeff7-b492-4218-b312-701ec99ee0cc",
    domain="chrome",
    members=[member],
  )
  step = TraceStep(
    task_id=bundle.task_id,
    seed=0,
    step=1,
    screenshot_path=member,
  )

  with zipfile.ZipFile(zip_path) as zf:
    local = extract_screenshot_for_judge(zf, bundle, step, tmp_path / "work")

  assert local is not None
  assert local.exists()
  assert local.read_bytes() == png_bytes
