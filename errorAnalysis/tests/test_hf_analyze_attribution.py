"""End-to-end adapter + Tier-1 attribution on fixture episodes."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cua_failure_analysis.adapters.base import EpisodeBundle
from cua_failure_analysis.adapters.opencua_osworld import normalize_opencua_episode
from cua_failure_analysis.attribution.pipeline import attribute_run
from cua_failure_analysis.taxonomy import FailureLeaf
from cua_failure_analysis.trace.schema import AttributionResult

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "hf_osworld_analyze.py"


def _load_analyze_module():
  if "hf_osworld_analyze" in sys.modules:
    return sys.modules["hf_osworld_analyze"]
  spec = importlib.util.spec_from_file_location("hf_osworld_analyze", SCRIPT_PATH)
  module = importlib.util.module_from_spec(spec)
  sys.modules["hf_osworld_analyze"] = module
  spec.loader.exec_module(module)
  return module


def test_load_phase_task_ids_pilot(tmp_path: Path):
  module = _load_analyze_module()
  tasks_file = tmp_path / "stratified_tasks.json"
  tasks_file.write_text(
    json.dumps(
      {
        "pilot_task_ids": ["a", "b", "c"],
        "tasks": [{"task_id": x} for x in ["a", "b", "c", "d", "e"]],
      }
    )
  )
  assert module.load_phase_task_ids("pilot", tasks_file) == {"a", "b", "c"}
  assert module.load_phase_task_ids("core", tasks_file) == {"a", "b", "c", "d", "e"}
  assert module.load_phase_task_ids("all", tasks_file) is None


def test_load_phase_task_ids_missing_file(tmp_path: Path):
  module = _load_analyze_module()
  with pytest.raises(FileNotFoundError):
    module.load_phase_task_ids("pilot", tmp_path / "nope.json")


def test_looping_episode_gets_action_looping_label(tmp_path: Path):
  task_id = "4c26e3f3-3a14-4d86-b44a-d3cedebbb487"
  episode_dir = tmp_path / f"multi_apps/{task_id}"
  episode_dir.mkdir(parents=True)
  (episode_dir / "traj.jsonl").write_bytes((FIXTURES / "traj_looping.jsonl").read_bytes())
  (episode_dir / "result.txt").write_text((FIXTURES / "result_looping_failed.txt").read_text())

  bundle = EpisodeBundle(
    episode_id=f"multi_apps/{task_id}",
    task_id=task_id,
    domain="multi_apps",
    members=[f"multi_apps/{task_id}/traj.jsonl", f"multi_apps/{task_id}/result.txt"],
  )
  result = normalize_opencua_episode(
    bundle,
    list(episode_dir.parent.rglob("*")),
    model_id="opencua-a3b",
    package="opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip",
  )
  trace_path = tmp_path / "trace.jsonl"
  with trace_path.open("w", encoding="utf-8") as f:
    for step in result.steps:
      f.write(step.model_dump_json() + "\n")

  attr = attribute_run(trace_path, instruction=result.manifest.instruction)
  assert attr.primary_mode == FailureLeaf.ACTION_LOOPING.value
  assert attr.tier_used == "programmatic"


def test_mock_judge_resolves_unresolved_fixture(tmp_path: Path):
  task_id = "4188d3a4-077d-46b7-9c86-23e1a036f6c1"
  episode_dir = tmp_path / f"libreoffice_calc/{task_id}"
  episode_dir.mkdir(parents=True)
  (episode_dir / "traj.jsonl").write_bytes((FIXTURES / "traj_failed.jsonl").read_bytes())
  (episode_dir / "result.txt").write_text((FIXTURES / "result_failed.txt").read_text())

  bundle = EpisodeBundle(
    episode_id=f"libreoffice_calc/{task_id}",
    task_id=task_id,
    domain="libreoffice_calc",
    members=[f"libreoffice_calc/{task_id}/traj.jsonl", f"libreoffice_calc/{task_id}/result.txt"],
  )
  norm = normalize_opencua_episode(
    bundle,
    list(episode_dir.parent.rglob("*")),
    model_id="opencua-a3b",
    package="opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip",
  )
  trace_path = tmp_path / "trace_failed.jsonl"
  with trace_path.open("w", encoding="utf-8") as f:
    for step in norm.steps:
      f.write(step.model_dump_json() + "\n")

  mock_judge = MagicMock()
  mock_judge.classify.return_value = AttributionResult(
    primary_mode=FailureLeaf.GOAL_HALLUCINATION.value,
    tier_used="judge",
    confidence=0.7,
    t_star=norm.steps[-1].step,
    evidence_cot_span="mock judge",
  )

  attr = attribute_run(trace_path, instruction=norm.manifest.instruction, judge=mock_judge)
  if attr.tier_used == "judge":
    assert mock_judge.classify.called
    assert attr.primary_mode == FailureLeaf.GOAL_HALLUCINATION.value
  else:
    assert attr.tier_used == "programmatic"
