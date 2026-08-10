"""Screenshot extraction from HF zip members for judge vision input."""

from __future__ import annotations

import zipfile
from pathlib import Path

from cua_failure_analysis.adapters.base import EpisodeBundle
from cua_failure_analysis.trace.schema import TraceStep


def resolve_screenshot_member(bundle: EpisodeBundle, step: TraceStep) -> str | None:
  screenshot = step.screenshot_path
  if not screenshot:
    return None
  if screenshot in bundle.members:
    return screenshot
  name = Path(screenshot).name
  for member in bundle.members:
    if member.endswith(f"/{name}") or member.endswith(name):
      return member
  candidate = f"{bundle.episode_id}/{name}"
  if candidate in bundle.members:
    return candidate
  return None


def safe_extract_members(zf: zipfile.ZipFile, members: list[str], dest: Path) -> list[Path]:
  import shutil

  extracted: list[Path] = []
  dest = dest.resolve()
  for member in members:
    target = (dest / member).resolve()
    if not str(target).startswith(str(dest)):
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, target.open("wb") as out:
      shutil.copyfileobj(src, out)
    extracted.append(target)
  return extracted


def extract_screenshot_for_judge(
  zf: zipfile.ZipFile,
  bundle: EpisodeBundle,
  step: TraceStep,
  work_dir: Path,
) -> Path | None:
  member = resolve_screenshot_member(bundle, step)
  if member is None:
    return None
  dest_root = work_dir / "screenshots" / bundle.episode_id.replace("/", "__")
  dest_root.mkdir(parents=True, exist_ok=True)
  extracted = safe_extract_members(zf, [member], dest_root)
  if not extracted:
    return None
  return extracted[0]
