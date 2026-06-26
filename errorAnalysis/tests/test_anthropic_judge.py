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


@patch("cua_failure_analysis.judge.anthropic_client.Anthropic")
def test_anthropic_judge_recovers_json_after_prose(mock_anthropic_cls):
  """The judge often reasons before emitting JSON; we must still parse it."""
  mock_client = MagicMock()
  mock_anthropic_cls.return_value = mock_client
  usage = MagicMock(input_tokens=2000, output_tokens=300)
  prose = (
    "Looking at this step, the agent clicks the static label instead of the "
    "input field.\n\nHere is my assessment:\n"
    '{"primary_mode": "Text Matching Bias", "secondary_modes": [], '
    '"propagated": false, "evidence_cot_span": "clicked label", "confidence": 0.7}'
  )
  text_block = MagicMock(type="text", text=prose)
  mock_client.messages.create.return_value = MagicMock(content=[text_block], usage=usage)

  judge = AnthropicJudge(AnthropicJudgeConfig(api_key="test-key"))
  result = judge.classify(_step(), instruction="Click Done", previous_steps=[])

  assert result.primary_mode == "Text Matching Bias"
  assert result.confidence == 0.7
