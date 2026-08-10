"""Shared fixtures: a small in-tmp eval set so tests never touch data/."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "errorAnalysis" / "src"))

from auto_research.objective import _hash_eval_content, load_eval_set  # noqa: E402

DONE_BTN = {"role": "button", "name": "Done", "bbox": [200, 100, 240, 130], "interactive": True}


def _step(task_id, n, coords, cot, eval_passed=None):
  return {
    "task_id": task_id,
    "seed": 0,
    "step": n,
    "screenshot_path": None,
    "action": {"type": "click"},
    "coords": coords,
    "cot": cot,
    "eval_signals": {"failed": True} if eval_passed is False else {},
    "a11y_snippet": [DONE_BTN],
    "task_tags": [],
    "instruction": "Click Done to save",
    "eval_passed": eval_passed,
    "state_hash": "s0",
  }


def make_eval_set(root: Path):
  """3 calibration + 2 holdout cases; loop-findable improvement: min_repeat=2."""
  cases = [
    # 3-rep loop: baseline catches.
    ("loop3", "calibration", ["Action Looping (Repetition)"],
     [_step("loop3", i, [220.0, 115.0], "Click Done.", False if i == 3 else None)
      for i in (1, 2, 3)]),
    # 2-rep loop: needs min_repeat=2.
    ("loop2", "calibration", ["Action Looping (Repetition)"],
     [_step("loop2", 1, [10.0, 10.0], "Open menu first."),
      _step("loop2", 2, [220.0, 115.0], "Click Done."),
      _step("loop2", 3, [220.0, 115.0], "Click Done.", False)]),
    # Far miss: Location Hallucination, baseline catches.
    ("far", "calibration", ["Location Hallucination"],
     [_step("far", 1, [700.0, 400.0], "Clicking Done now.", False)]),
    # Holdout twins.
    ("loop2-h", "holdout", ["Action Looping (Repetition)"],
     [_step("loop2-h", 1, [12.0, 12.0], "Scroll to it."),
      _step("loop2-h", 2, [220.0, 115.0], "Click Done."),
      _step("loop2-h", 3, [220.0, 115.0], "Click Done.", False)]),
    ("far-h", "holdout", ["Location Hallucination"],
     [_step("far-h", 1, [650.0, 380.0], "I see Done; clicking.", False)]),
  ]
  manifest_cases = []
  for case_id, split, gold, steps in cases:
    d = root / "traces" / case_id
    d.mkdir(parents=True)
    with (d / "trace.jsonl").open("w") as f:
      for s in steps:
        f.write(json.dumps(s, sort_keys=True) + "\n")
    manifest_cases.append(
      {
        "case_id": case_id,
        "split": split,
        "trace": f"traces/{case_id}/trace.jsonl",
        "gold_modes": gold,
        "instruction": "Click Done to save",
        "task_tags": [],
        "reference_summary": "human: click Done once",
        "osworld_score": 0.0,
        "eval_output": "evaluator: file not created",
      }
    )
  manifest = {"version": 1, "cases": manifest_cases}
  manifest["content_hash"] = _hash_eval_content(manifest, root)
  (root / "eval_manifest.json").write_text(json.dumps(manifest, indent=2))
  return root


@pytest.fixture
def eval_set(tmp_path):
  return load_eval_set(make_eval_set(tmp_path / "eval_set"))
