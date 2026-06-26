"""Tests for OpenCUA OSWorld adapter normalization."""

from pathlib import Path

from cua_failure_analysis.adapters.base import EpisodeBundle
from cua_failure_analysis.adapters.opencua_osworld import normalize_opencua_episode

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"


def _bundle(task_id: str = "1334ca3e-f9e3-4db8-9ca7-b4c653be7d17") -> EpisodeBundle:
  domain = "libreoffice_calc"
  episode_id = f"{domain}/{task_id}"
  return EpisodeBundle(
    episode_id=episode_id,
    task_id=task_id,
    domain=domain,
    members=[
      f"{episode_id}/traj.jsonl",
      f"{episode_id}/result.txt",
      f"{episode_id}/step_1_20250730@083931.png",
    ],
  )


def test_normalize_success_episode(tmp_path: Path):
  episode_dir = tmp_path / "libreoffice_calc/1334ca3e-f9e3-4db8-9ca7-b4c653be7d17"
  episode_dir.mkdir(parents=True)
  (episode_dir / "traj.jsonl").write_bytes((FIXTURES / "traj_step.jsonl").read_bytes())
  (episode_dir / "result.txt").write_text((FIXTURES / "result_success.txt").read_text())

  result = normalize_opencua_episode(
    _bundle(),
    list(episode_dir.parent.rglob("*")),
    model_id="opencua-a3b",
    package="opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip",
  )

  assert result.manifest.success is True
  assert len(result.steps) == 2
  step = result.steps[0]
  assert step.step == 1
  assert step.coords == [1820.0, 1065.0]
  assert step.action["type"] == "drag"
  assert "zoom" in step.cot.lower()
  assert step.screenshot_path.endswith("step_1_20250730@083931.png")


def test_normalize_failed_episode(tmp_path: Path):
  episode_dir = tmp_path / "libreoffice_calc/4188d3a4-077d-46b7-9c86-23e1a036f6c1"
  episode_dir.mkdir(parents=True)
  (episode_dir / "traj.jsonl").write_bytes((FIXTURES / "traj_failed.jsonl").read_bytes())
  (episode_dir / "result.txt").write_text((FIXTURES / "result_failed.txt").read_text())

  bundle = _bundle(task_id="4188d3a4-077d-46b7-9c86-23e1a036f6c1")
  result = normalize_opencua_episode(
    bundle,
    list(episode_dir.parent.rglob("*")),
    model_id="opencua-a3b",
    package="opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip",
  )

  assert result.manifest.success is False
  assert result.steps[-1].eval_passed is False
  assert result.steps[0].action["type"] == "click"
