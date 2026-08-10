"""Unit tests for eval_bundle formatting without requiring full vendor cache."""

from __future__ import annotations

from pathlib import Path

from cua_failure_analysis.osworld.eval_bundle import format_eval_bundle, getter_name_for_result_type


SAMPLE_TASK = {
  "id": "06fe7178-4491-4589-810f-2e2bc9502122",
  "instruction": "Can you make my computer bring back the last tab I shut down?",
  "config": [
    {"type": "launch", "parameters": {"command": ["google-chrome", "--remote-debugging-port=1337"]}},
    {
      "type": "chrome_open_tabs",
      "parameters": {"urls_to_open": ["https://www.lonelyplanet.com", "https://www.airbnb.com"]},
    },
  ],
  "evaluator": {
    "func": "is_expected_tabs",
    "result": {"type": "open_tabs_info"},
    "expected": {
      "type": "rule",
      "rules": {
        "type": "url",
        "urls": [
          "https://www.lonelyplanet.com",
          "https://www.airbnb.com",
          "https://www.tripadvisor.com",
        ],
      },
    },
  },
}


def test_getter_name_for_result_type():
  assert getter_name_for_result_type("open_tabs_info") == "get_open_tabs_info"
  assert getter_name_for_result_type("get_vm_file") == "get_vm_file"
  assert getter_name_for_result_type(None) is None


def test_format_eval_bundle_with_inline_summary(tmp_path: Path):
  summary = tmp_path / "is_expected_tabs.md"
  summary.write_text(
    "# is_expected_tabs\n\n## Purpose\nCheck open tabs.\n\n## Source excerpt\n```python\npass\n```\n",
    encoding="utf-8",
  )
  text = format_eval_bundle(
    SAMPLE_TASK,
    result_txt=0.0,
    func_summary_path=summary,
    pin_dir=tmp_path,
  )
  assert "OSWorld outcome: fail (result.txt=0.0)" in text
  assert "bring back the last tab" in text
  assert "Evaluator function: is_expected_tabs" in text
  assert "open_tabs_info → get_open_tabs_info" in text
  assert "Check open tabs." in text
  assert "```python" not in text  # source excerpt stripped from summary body
  assert "chrome_open_tabs" in text
