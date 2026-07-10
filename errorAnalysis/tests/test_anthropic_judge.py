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


@patch("cua_failure_analysis.judge.anthropic_client.Anthropic")
def test_anthropic_judge_prompt_has_structured_action_and_human_images(
  mock_anthropic_cls, tmp_path
):
  mock_client = MagicMock()
  mock_anthropic_cls.return_value = mock_client
  usage = MagicMock(input_tokens=100, output_tokens=20)
  text_block = MagicMock(
    type="text",
    text='{"primary_mode": "Click Region Error", "confidence": 0.6}',
  )
  mock_client.messages.create.return_value = MagicMock(content=[text_block], usage=usage)

  human_img = tmp_path / "human_step_1_obs.png"
  human_img.write_bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
  )
  model_img = tmp_path / "model_obs.png"
  model_img.write_bytes(human_img.read_bytes())

  step = TraceStep(
    task_id="t1",
    seed=0,
    step=2,
    cot="Click the tab",
    screenshot_path=str(model_img),
    action={
      "type": "click",
      "raw_code": "pyautogui.click(1576, 364)",
      "model_code": "pyautogui.click(x=0.821, y=0.120)",
      "stated_intent": "Click recently closed tab",
      "grounding_mismatch": True,
    },
  )
  judge = AnthropicJudge(AnthropicJudgeConfig(api_key="test-key"))
  judge.classify(
    step,
    instruction="Bring back the last tab",
    previous_steps=[],
    eval_bundle="Evaluator function: is_expected_tabs",
    canonical_instruction="Can you make my computer bring back the last tab I shut down?",
    human_reference_steps=[
      {"action_text": "`HOTKEY` Ctrl+Shift+T", "image_path": str(human_img)},
    ],
  )

  call_kwargs = mock_client.messages.create.call_args.kwargs
  content = call_kwargs["messages"][0]["content"]
  image_blocks = [c for c in content if c.get("type") == "image"]
  text_blocks = [c for c in content if c.get("type") == "text"]
  assert len(image_blocks) == 2  # human obs + model obs
  assert text_blocks
  prompt = text_blocks[0]["text"]
  assert "Executed action (trajectory" in prompt
  assert "Model code (CoT" in prompt
  assert "NON-BINDING" in prompt
  assert "is_expected_tabs" in prompt
  assert "Grounding pre-check: True" in prompt
  assert "NON-BINDING" in call_kwargs["system"] or "non-binding" in call_kwargs["system"].lower()
