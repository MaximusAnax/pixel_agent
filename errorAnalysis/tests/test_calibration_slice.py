"""Tests for calibration slice selection."""

from cua_failure_analysis.labeling.calibration_slice import select_calibration_tasks


def run(task, model, success, judge=None):
  return {
    "task_id": task,
    "model_id": model,
    "success": success,
    "judge_primary_mode": judge,
  }


def test_selects_matching_task():
  runs = [
    run("t1", "human", True),
    run("t1", "opencua-3b", False, "Click Region Error"),
    run("t1", "opencua-7b", False, "Action Looping (Repetition)"),
  ]
  assert select_calibration_tasks(runs) == ["t1"]


def test_rejects_human_failure():
  runs = [
    run("t1", "human", False),
    run("t1", "opencua-3b", False, "Click Region Error"),
    run("t1", "opencua-7b", False, "Click Region Error"),
  ]
  assert select_calibration_tasks(runs) == []


def test_rejects_any_agent_success():
  runs = [
    run("t1", "human", True),
    run("t1", "opencua-3b", True),
    run("t1", "opencua-7b", False, "Click Region Error"),
  ]
  assert select_calibration_tasks(runs) == []


def test_rejects_missing_agent_model():
  runs = [
    run("t1", "human", True),
    run("t1", "opencua-3b", False, "Click Region Error"),
  ]
  assert select_calibration_tasks(runs) == []


def test_requires_judge_conclusion():
  runs = [
    run("t1", "human", True),
    run("t1", "opencua-3b", False, "Unresolved"),
    run("t1", "opencua-7b", False, None),
  ]
  assert select_calibration_tasks(runs) == []
  assert select_calibration_tasks(runs, require_judge_conclusion=False) == ["t1"]


def test_limit_and_determinism():
  runs = []
  for i in range(8):
    runs += [
      run(f"t{i}", "human", True),
      run(f"t{i}", "opencua-3b", False, "Click Region Error"),
      run(f"t{i}", "opencua-7b", False, "Click Region Error"),
    ]
  picked = select_calibration_tasks(runs, limit=5)
  assert len(picked) == 5
  assert picked == sorted(picked)


def test_model_id_normalization():
  runs = [
    run("t1", "HumanAgent".replace("Agent", ""), True),  # "Human"
    run("t1", "OpenCUA_3B", False, "Click Region Error"),
    run("t1", "opencua-7b", False, "Click Region Error"),
  ]
  assert select_calibration_tasks(runs) == ["t1"]
