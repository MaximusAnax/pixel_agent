"""End-to-end adapter + Tier-1 attribution on fixture episodes."""

from pathlib import Path

from cua_failure_analysis.adapters.base import EpisodeBundle
from cua_failure_analysis.adapters.opencua_osworld import normalize_opencua_episode
from cua_failure_analysis.attribution.pipeline import attribute_run
from cua_failure_analysis.taxonomy import FailureLeaf

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"


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
