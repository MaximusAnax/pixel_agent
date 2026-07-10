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
  assert "pyautogui.moveTo" in step.action["model_code"]
  assert "0.948" in step.action["model_code"]
  assert step.action["stated_intent"]
  assert step.action["grounding_mismatch"] is False
  assert step.action["coords_model_normalized"] is not None
  assert step.action["coords_executed"] is not None


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
  # Fixture task is not in pilot vendor cache — eval_message falls back.
  assert result.manifest.eval_message


def test_grounding_mismatch_detection():
  from cua_failure_analysis.osworld.grounding import compare_proposed_vs_executed

  match = compare_proposed_vs_executed(
    "pyautogui.click(x=0.821, y=0.337)",
    "pyautogui.click(1576, 364)",
  )
  assert match["grounding_mismatch"] is False

  mismatch = compare_proposed_vs_executed(
    "pyautogui.click(x=0.821, y=0.120)",
    "pyautogui.click(1576, 364)",
  )
  assert mismatch["grounding_mismatch"] is True
  assert mismatch["distance_frac"] is not None
  assert mismatch["distance_frac"] > 0.05


def test_normalize_pilot_task_loads_osworld_context(tmp_path: Path):
  """When task_id is in the vendored pilot cache, populate eval bundle + human ref."""
  task_id = "06fe7178-4491-4589-810f-2e2bc9502122"
  episode_dir = tmp_path / f"chrome/{task_id}"
  episode_dir.mkdir(parents=True)
  # Minimal one-step traj using fixture response shape.
  traj = (
    '{"step_num": 1, "action": "DONE", "response": "# Step 1:\\n## Thought:\\nx\\n'
    '## Action:\\nDone.\\n\\n## Code:\\n```python\\n# done\\n```\\n", '
    '"reward": 0, "done": true, "screenshot_file": "step_1.png"}\n'
  )
  (episode_dir / "traj.jsonl").write_text(traj, encoding="utf-8")
  (episode_dir / "result.txt").write_text("0.0\n", encoding="utf-8")

  bundle = EpisodeBundle(
    episode_id=f"chrome/{task_id}",
    task_id=task_id,
    domain="chrome",
    members=[f"chrome/{task_id}/traj.jsonl", f"chrome/{task_id}/result.txt"],
  )
  result = normalize_opencua_episode(
    bundle,
    list(episode_dir.parent.rglob("*")),
    model_id="opencua-a3b",
    package="test.zip",
  )
  assert "bring back the last tab" in result.manifest.canonical_instruction.lower()
  assert "is_expected_tabs" in result.manifest.eval_bundle
  assert result.manifest.human_reference_actions
  assert any("HOTKEY" in a for a in result.manifest.human_reference_actions)
  assert result.steps[-1].eval_signals.get("message")
  assert "is_expected_tabs" in result.steps[-1].eval_signals["message"]
  assert result.manifest.eval_message == result.manifest.eval_bundle
