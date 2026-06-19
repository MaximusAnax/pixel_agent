"""Tests for attribution pipeline."""

import json
from pathlib import Path

from cua_failure_analysis.attribution.pipeline import attribute_run
from cua_failure_analysis.taxonomy import FailureLeaf


def test_attribute_sample_trace(tmp_path: Path):
  trace_src = Path(__file__).parents[1] / "data" / "pilot" / "sample_trace.jsonl"
  trace_path = tmp_path / "trace.jsonl"
  trace_path.write_text(trace_src.read_text())
  result = attribute_run(trace_path, instruction="Click Done to save")
  assert result.primary_mode == FailureLeaf.ACTION_LOOPING.value
  assert result.t_star == 5
