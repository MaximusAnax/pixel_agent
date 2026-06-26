"""Tests for Anthropic judge client."""

from unittest.mock import MagicMock, patch

from cua_failure_analysis.judge.anthropic_client import AnthropicJudge, AnthropicJudgeConfig
from cua_failure_analysis.trace.schema import TraceStep


def _step() -> TraceStep:
  return TraceStep(
    task_id="t1",
    seed=0,
    step=3,
    cot="I will click the Done button.",
    action={"type": "click", "raw_code": "pyautogui.click(100, 200)"},
    coords=[100.0, 200.0],
    instruction="Click Done",
  )


@patch("cua_failure_analysis.judge.anthropic_client.Anthropic")
def test_anthropic_judge_classify(mock_anthropic_cls):
  mock_client = MagicMock()
  mock_anthropic_cls.return_value = mock_client
  usage = MagicMock(input_tokens=1200, output_tokens=80)
  text_block = MagicMock(type="text", text='{"primary_mode": "Click Region Error", "confidence": 0.8}')
  mock_client.messages.create.return_value = MagicMock(content=[text_block], usage=usage)

  judge = AnthropicJudge(AnthropicJudgeConfig(api_key="test-key", model="claude-sonnet-4-20250514"))
  result = judge.classify(_step(), instruction="Click Done", previous_steps=[])

  assert result.primary_mode == "Click Region Error"
  assert result.tier_used == "judge"
  assert judge.last_usage is not None
  assert judge.last_usage.input_tokens == 1200
  mock_client.messages.create.assert_called_once()
