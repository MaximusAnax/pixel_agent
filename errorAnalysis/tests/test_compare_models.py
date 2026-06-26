"""Tests for the cross-model comparison aggregator."""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "compare_models.py"


def _load_module():
  if "compare_models" in sys.modules:
    return sys.modules["compare_models"]
  spec = importlib.util.spec_from_file_location("compare_models", SCRIPT_PATH)
  module = importlib.util.module_from_spec(spec)
  sys.modules["compare_models"] = module
  spec.loader.exec_module(module)
  return module


def _make_run(
  run_dir: Path,
  model_id: str,
  manifests: list[dict],
  labels: list[dict],
) -> None:
  run_dir.mkdir(parents=True, exist_ok=True)
  (run_dir / "run_metadata.json").write_text(
    json.dumps({"model_id": model_id, "package": f"{model_id}.zip"})
  )
  (run_dir / "episode_manifests.json").write_text(json.dumps(manifests))
  with (run_dir / "failure_labels.jsonl").open("w", encoding="utf-8") as f:
    for row in labels:
      f.write(json.dumps(row) + "\n")


def _label(episode_id: str, primary: str, **extra) -> dict:
  base = {
    "status": "failed",
    "episode_id": episode_id,
    "primary_mode": primary,
    "secondary_modes": [],
    "propagated": False,
    "tier_used": "judge",
  }
  base.update(extra)
  return base


def test_build_comparison_basic(tmp_path: Path):
  module = _load_module()

  # Model A: 4 episodes, 2 failed (one perception, one cognitive).
  run_a = tmp_path / "runA"
  _make_run(
    run_a,
    "opencua-a3b-cot-l2-action-history-3image-",
    manifests=[
      {"task_id": "t1", "success": False},
      {"task_id": "t2", "success": False},
      {"task_id": "t3", "success": True},
      {"task_id": "t4", "success": True},
    ],
    labels=[
      _label("chrome/t1", "Click Region Error"),
      _label("chrome/t2", "Action Looping (Repetition)", propagated=True,
             meta_labels=["propagated_failure"]),
    ],
  )

  # Model B: 4 episodes, 3 failed (two cognitive, one with secondary mode).
  run_b = tmp_path / "runB"
  _make_run(
    run_b,
    "opencua-7b-cot-l2-action-history-3image-",
    manifests=[
      {"task_id": "t1", "success": False},
      {"task_id": "t2", "success": True},
      {"task_id": "t3", "success": False},
      {"task_id": "t4", "success": False},
    ],
    labels=[
      _label("chrome/t1", "Reasoning Drift", secondary_modes=["Goal Hallucination"]),
      _label("calc/t3", "Goal Hallucination"),
      _label("calc/t4", "Action Looping (Repetition)"),
    ],
  )

  comp = module.build_comparison([run_a, run_b])

  assert comp["models"] == ["opencua-a3b", "opencua-7b"]

  a = comp["per_model"]["opencua-a3b"]
  b = comp["per_model"]["opencua-7b"]

  # Failure rate from manifests.
  assert a["n_episodes"] == 4 and a["n_failed"] == 2
  assert a["failure_rate"] == 0.5
  assert b["n_failed"] == 3 and b["failure_rate"] == 0.75

  # Perception vs cognitive split.
  assert a["perception_vs_cognitive"]["perception"]["count"] == 1
  assert a["perception_vs_cognitive"]["cognitive"]["count"] == 1
  assert b["perception_vs_cognitive"]["cognitive"]["count"] == 3
  assert b["perception_vs_cognitive"]["perception"]["count"] == 0

  # Prevalence rows carry CIs.
  prev_a = {r["leaf"]: r for r in a["prevalence_table"]}
  click_row = prev_a["Click Region Error"]
  assert click_row["count"] == 1
  assert "ci_low" in click_row and "ci_high" in click_row
  assert click_row["ci_high"] >= click_row["prevalence"] >= click_row["ci_low"]

  # Propagation captured for Action Looping in model A.
  assert a["propagation"]["Action Looping (Repetition)"]["propagated"] == 1
  assert a["propagation"]["Action Looping (Repetition)"]["rate"] == 1.0

  # Co-occurrence from secondary modes in model B.
  assert b["cooccurrence"]["Reasoning Drift"]["Goal Hallucination"] == 1

  # Task overlap reflects differing failure sets: A={t1,t2}, B={t1,t3,t4}.
  overlap = comp["pilot_task_overlap"]
  assert overlap["intersection"] == ["t1"]
  assert overlap["n_union"] == 4


def test_render_markdown_smoke(tmp_path: Path):
  module = _load_module()
  run_a = tmp_path / "runA"
  _make_run(
    run_a, "opencua-a3b-cot-l2-action-history-3image-",
    manifests=[{"task_id": "t1", "success": False}],
    labels=[_label("chrome/t1", "Reasoning Drift")],
  )
  run_b = tmp_path / "runB"
  _make_run(
    run_b, "opencua-7b-cot-l2-action-history-3image-",
    manifests=[{"task_id": "t1", "success": False}],
    labels=[_label("chrome/t1", "Click Region Error")],
  )
  comp = module.build_comparison([run_a, run_b])
  md = module.render_markdown(comp)
  assert "Multi-Model Failure Prevalence Comparison" in md
  assert "opencua-a3b" in md and "opencua-7b" in md
  assert "Perception vs Cognitive" in md
