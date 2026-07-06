"""Tests for the whole-trajectory judge (taxonomy/schema, shared parsing, the
Anthropic backend's block-mapping + structured output, and trajectory parsing).

These avoid heavy/optional deps: vLLM is never imported, and the Anthropic client
is faked (the backend imports ``anthropic`` lazily), so the suite runs on CPU
without an API key.
"""

from __future__ import annotations

from cua_failure_analysis.trajectory_judge import judge_common as jc
from cua_failure_analysis.trajectory_judge import parse_trajs as pt
from cua_failure_analysis.trajectory_judge.backends.anthropic_api import (
    AnthropicConfig,
    AnthropicTrajectoryJudge,
    TOOL_NAME,
)
from cua_failure_analysis.trajectory_judge.judge_prompt import SYSTEM_PROMPT, build_messages
from cua_failure_analysis.trajectory_judge.schema import Classification


def _traj() -> dict:
    return {
        "model": "opencua-7b",
        "domain": "chrome",
        "task_id": "t1",
        "instruction": "Open settings",
        "reward": 0.0,
        "num_steps": 3,
        "steps": [
            {"idx": i, "screenshot_path": None, "reasoning": f"r{i}", "action": f"click {i}"}
            for i in (1, 2, 3)
        ],
    }


def _valid_classification(mode="action_looping", category="perception_grounding") -> dict:
    return {
        "analysis": f"...therefore the category is cognitive_planning and the specific mode is {mode}.",
        "category": category,
        "primary_failure_mode": mode,
        "failing_step": 2,
        "secondary_failure_modes": [],
        "confidence": 0.7,
    }


def test_schema_is_valid_anthropic_tool_input():
    schema = Classification.model_json_schema()
    assert schema["type"] == "object"
    assert "primary_failure_mode" in schema["required"]


def test_parse_json_obj_derives_authoritative_category():
    # category claimed by the model is wrong; the mode is trusted and category derived.
    parsed, ok = jc.parse_json_obj(_valid_classification(category="perception_grounding"))
    assert ok
    assert parsed["category"] == "cognitive_planning"
    assert parsed["category_model"] == "perception_grounding"
    assert parsed["category_mismatch"] is True


def test_parse_json_text_roundtrip():
    import json

    parsed, ok = jc.parse_json_text(json.dumps(_valid_classification(category="cognitive_planning")))
    assert ok
    assert parsed["category_mismatch"] is False


def test_invalid_mode_rejected():
    parsed, ok = jc.parse_json_obj({**_valid_classification(), "primary_failure_mode": "nope"})
    assert ok is False


def test_build_record_shape():
    out = jc.JudgeOutput(parsed={"x": 1}, parse_ok=True, raw="{}", n_images=2,
                         usage={"input_tokens": 10, "output_tokens": 5, "model": "m"})
    rec = jc.build_record(_traj(), "api", "claude-x", out)
    assert rec["uid"] == "opencua-7b/chrome/t1"
    assert rec["judge_backend"] == "api" and rec["judge_model"] == "claude-x"
    assert rec["n_images"] == 2 and rec["usage"]["input_tokens"] == 10


def test_build_messages_structure():
    system, user = build_messages(_traj(), [])
    assert system["role"] == "system" and system["content"] == SYSTEM_PROMPT
    assert user["role"] == "user" and all(b["type"] == "text" for b in user["content"])


class _FakeUsage:
    input_tokens = 123
    output_tokens = 45


class _ToolBlock:
    type = "tool_use"
    name = TOOL_NAME

    def __init__(self, data):
        self.input = data


class _FakeResponse:
    def __init__(self, data):
        self.content = [_ToolBlock(data)]
        self.usage = _FakeUsage()


def test_anthropic_backend_tool_use(monkeypatch):
    judge = AnthropicTrajectoryJudge(AnthropicConfig(api_key="test"))
    captured = {}

    class _Messages:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return _FakeResponse(_valid_classification(category="cognitive_planning"))

    class _FakeClient:
        messages = _Messages()

    judge._client = _FakeClient()  # bypass lazy _ensure_client (no anthropic/network)
    result = judge.classify(_traj())

    assert result.parse_ok
    assert result.parsed["primary_failure_mode"] == "action_looping"
    assert result.usage["input_tokens"] == 123
    # forced structured output + shared system prompt
    assert captured["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert captured["system"] == SYSTEM_PROMPT
    assert captured["temperature"] == 0.0


def test_anthropic_backend_text_fallback():
    """No tool block -> fall back to parsing JSON from text content."""
    import json

    class _TextBlock:
        type = "text"
        text = json.dumps(_valid_classification(category="cognitive_planning"))

    class _Resp:
        content = [_TextBlock()]
        usage = _FakeUsage()

    class _FakeClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                return _Resp()

    judge = AnthropicTrajectoryJudge(AnthropicConfig(api_key="test"))
    judge._client = _FakeClient()
    result = judge.classify(_traj())
    assert result.parse_ok and result.parsed["primary_failure_mode"] == "action_looping"


# ---- parse_trajs normalization ----

def test_clean_raw_response_single_segment():
    assert pt.clean_raw_response("[TEXT] hello world") == "hello world"


def test_clean_raw_response_drops_tool_use_keeps_thinking():
    raw = "[THINKING] plan A [TEXT] doing it [TOOL_USE] click(1,2)"
    out = pt.clean_raw_response(raw)
    assert "plan A" in out and "doing it" in out and "click(1,2)" not in out


def test_extract_reasoning_opencua_vs_claude():
    # OpenCUA: reasoning is top-level `response`; action is a string
    opencua = {"step_num": 1, "action": "pyautogui.click(1,2)", "response": "## Thought: go"}
    assert pt.extract_reasoning(opencua) == "## Thought: go"
    assert pt.extract_action(opencua) == "pyautogui.click(1,2)"

    # Claude: reasoning is in action.raw_response; action is command
    claude = {
        "step_num": 1,
        "action": {"action_type": "tool_use", "command": "pyautogui.click(3,4)",
                   "raw_response": "[THINKING] hmm [TEXT] narration"},
        "response": "narration",
    }
    reasoning = pt.extract_reasoning(claude)
    assert "hmm" in reasoning and "narration" in reasoning
    assert pt.extract_action(claude) == "pyautogui.click(3,4)"


def test_is_step_record_rejects_harness_errors():
    assert pt.is_step_record({"step_num": 1, "action": "x"}) is True
    assert pt.is_step_record({"Error": "boom"}) is False
