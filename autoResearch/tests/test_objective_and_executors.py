"""Objective scoring, hash pinning, and both executors."""

import json

import pytest

from auto_research.budget import BudgetExceeded, CostMeter, Pricing
from auto_research.candidates import candidate_from_dict
from auto_research.executors import DetectorExecutor, JudgeExecutor
from auto_research.objective import load_eval_set, score_predictions


def test_eval_set_loads_with_splits(eval_set):
  assert len(eval_set.split("calibration")) == 3
  assert len(eval_set.split("holdout")) == 2
  assert eval_set.content_hash


def test_hash_pinning_detects_tampering(tmp_path, eval_set):
  manifest_path = eval_set.root / "eval_manifest.json"
  manifest = json.loads(manifest_path.read_text())
  manifest["cases"][0]["gold_modes"] = ["Goal Hallucination"]  # tamper
  manifest_path.write_text(json.dumps(manifest))
  with pytest.raises(RuntimeError, match="Eval set modified"):
    load_eval_set(eval_set.root)


def test_score_predictions_requires_all_cases(eval_set):
  with pytest.raises(ValueError, match="missing"):
    score_predictions(eval_set, {})


def test_detector_baseline_partial(eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  preds = DetectorExecutor().run(baseline, eval_set)
  scores = score_predictions(eval_set, preds)
  # baseline catches loop3 + far, misses the 2-rep loops
  assert preds["loop3"] == frozenset({"Action Looping (Repetition)"})
  assert preds["loop2"] == frozenset()
  assert 0 < scores.calibration.primary < 1


def test_detector_min_repeat_2_fixes_both_splits(eval_set):
  improved = candidate_from_dict({"name": "mr2", "detectors": {"min_repeat": 2}})
  baseline = candidate_from_dict({"name": "baseline"})
  ex = DetectorExecutor()
  base_scores = score_predictions(eval_set, ex.run(baseline, eval_set))
  new_scores = score_predictions(eval_set, ex.run(improved, eval_set))
  assert new_scores.calibration.primary > base_scores.calibration.primary
  assert new_scores.holdout.primary > base_scores.holdout.primary


class FakeCompletions:
  def __init__(self, payloads):
    self.payloads = list(payloads)
    self.requests = []

  def create(self, **kwargs):
    self.requests.append(kwargs)

    class Msg:
      def __init__(self, content):
        self.content = content

    class Choice:
      def __init__(self, content):
        self.message = Msg(content)

    class Resp:
      def __init__(self, content):
        self.choices = [Choice(content)]

    return Resp(self.payloads.pop(0) if self.payloads else "{}")


class FakeClient:
  def __init__(self, payloads):
    self.chat = type("Chat", (), {})()
    self.chat.completions = FakeCompletions(payloads)


def test_judge_executor_v2_parses_modes(eval_set):
  cand = candidate_from_dict(
    {"name": "v2", "judge": {"protocol": "v2_multilabel", "anchors_path": None}}
  )
  payload = json.dumps({"modes": ["Action Looping (Repetition)", "NotALeaf"]})
  client = FakeClient([payload] * len(eval_set.cases))
  meter = CostMeter(pricing=Pricing.free(), cap_usd=25.0)
  preds = JudgeExecutor(client=client, meter=meter).run(cand, eval_set)
  assert preds["loop3"] == frozenset({"Action Looping (Repetition)"})  # invalid leaf dropped
  assert meter.calls == len(eval_set.cases)
  # v2 prompt carries reference + evaluator context
  user_text = client.chat.completions.requests[0]["messages"][1]["content"][0]["text"]
  assert "Reference (human) trajectory" in user_text
  assert "Evaluator test output" in user_text


def test_judge_executor_ablation_flags(eval_set):
  cand = candidate_from_dict(
    {
      "name": "v2-min",
      "judge": {
        "protocol": "v2_multilabel",
        "anchors_path": None,
        "include_reference_trajectory": False,
        "include_osworld_score": False,
        "include_eval_output": False,
      },
    }
  )
  client = FakeClient(["{}"] * len(eval_set.cases))
  meter = CostMeter(pricing=Pricing.free(), cap_usd=25.0)
  JudgeExecutor(client=client, meter=meter).run(cand, eval_set)
  user_text = client.chat.completions.requests[0]["messages"][1]["content"][0]["text"]
  assert "Reference (human) trajectory" not in user_text
  assert "OSWorld metric score" not in user_text
  assert "Evaluator test output" not in user_text


def test_judge_executor_stops_at_budget(eval_set):
  cand = candidate_from_dict(
    {"name": "v2", "judge": {"protocol": "v2_multilabel", "anchors_path": None}}
  )
  client = FakeClient(["{}"] * len(eval_set.cases))
  pricey = Pricing(input_per_mtok=1e9, output_per_mtok=1e9, image_tokens_each=0)
  meter = CostMeter(pricing=pricey, cap_usd=0.01)
  with pytest.raises(BudgetExceeded):
    JudgeExecutor(client=client, meter=meter).run(cand, eval_set)
  assert meter.calls == 0  # stopped BEFORE the first call, not after
