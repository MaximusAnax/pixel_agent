"""Tests for judge usage cost helpers."""

from cua_failure_analysis.judge.usage import (
  JudgeUsage,
  estimate_judge_cost_usd,
  summarize_judge_usage,
)


def test_estimate_judge_cost_usd():
  cost = estimate_judge_cost_usd("claude-sonnet-4-20250514", 1_000_000, 100_000)
  assert cost > 0


def test_summarize_judge_usage():
  rows = [
    {"input_tokens": 1000, "output_tokens": 100, "estimated_cost_usd": 0.01},
    {"input_tokens": 2000, "output_tokens": 200, "estimated_cost_usd": 0.02},
  ]
  summary = summarize_judge_usage(rows)
  assert summary["judge_calls"] == 2
  assert summary["input_tokens"] == 3000
  assert summary["estimated_cost_usd"] == 0.03


def test_judge_usage_dataclass_cost():
  usage = JudgeUsage(input_tokens=1000, output_tokens=500, model="claude-sonnet-4-20250514")
  assert usage.estimated_cost_usd > 0
