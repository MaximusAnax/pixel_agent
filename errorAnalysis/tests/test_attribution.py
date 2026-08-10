"""Tests for attribution pipeline."""

import json
from pathlib import Path

from cua_failure_analysis.attribution.pipeline import attribute_run
from cua_failure_analysis.taxonomy import FailureLeaf
from cua_failure_analysis.trace.schema import A11yElement, TraceStep


def test_attribute_sample_trace(tmp_path: Path):
  trace_src = Path(__file__).parents[1] / "data" / "pilot" / "sample_trace.jsonl"
  trace_path = tmp_path / "trace.jsonl"
  trace_path.write_text(trace_src.read_text())
  result = attribute_run(trace_path, instruction="Click Done to save")
  assert result.primary_mode == FailureLeaf.ACTION_LOOPING.value
  assert result.t_star == 5


def _write_trace(path: Path, steps: list[TraceStep]) -> None:
  with path.open("w", encoding="utf-8") as f:
    for step in steps:
      f.write(step.model_dump_json() + "\n")


def test_action_looping_marked_propagated_from_earlier_grounding(tmp_path: Path):
  done = A11yElement(role="button", name="Done", bbox=[80, 40, 120, 70], interactive=True)
  steps = [
    # Step 0: earlier root cause — CoT names Done but click lands just outside bbox.
    TraceStep(
      task_id="t1", seed=0, step=0, cot="Click the Done button", coords=[125, 55],
      state_hash="s0", a11y_snippet=[done],
    ),
    # Steps 1-3: identical looping clicks with unchanged state; last one fails.
    *[
      TraceStep(
        task_id="t1", seed=0, step=i, cot="clicking again", coords=[300, 300],
        state_hash="loop", a11y_snippet=[],
        eval_signals={"failed": True} if i == 3 else {},
        eval_passed=False if i == 3 else None,
      )
      for i in (1, 2, 3)
    ],
  ]
  trace_path = tmp_path / "trace.jsonl"
  _write_trace(trace_path, steps)
  result = attribute_run(trace_path, instruction="Click Done to save")
  assert result.primary_mode == FailureLeaf.ACTION_LOOPING.value
  assert result.propagated is True
  assert "propagated_failure" in result.meta_labels


def test_non_consequence_label_not_propagated(tmp_path: Path):
  done = A11yElement(role="button", name="Done", bbox=[80, 40, 120, 70], interactive=True)
  steps = [
    TraceStep(
      task_id="t1", seed=0, step=0, cot="Click the Done button", coords=[125, 55],
      state_hash="s0", a11y_snippet=[done], eval_signals={"failed": True}, eval_passed=False,
    ),
  ]
  trace_path = tmp_path / "trace.jsonl"
  _write_trace(trace_path, steps)
  result = attribute_run(trace_path, instruction="Click Done to save")
  assert result.primary_mode == FailureLeaf.CLICK_REGION_ERROR.value
  assert result.propagated is False
  assert result.meta_labels == []
