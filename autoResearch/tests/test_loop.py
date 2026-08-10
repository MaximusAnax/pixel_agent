"""Loop mechanics: keep/discard, dedupe, ledger, overfit flag, summary."""

import json

from auto_research.candidates import candidate_from_dict
from auto_research.executors import DetectorExecutor
from auto_research.loop import Ledger, LoopConfig, run_loop, write_summary
from auto_research.proposals import grid_proposals, queue_proposals


def _write(path, payload):
  path.write_text(payload, encoding="utf-8")
  return path


def test_loop_finds_min_repeat_improvement(tmp_path, eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  grid = _write(
    tmp_path / "grid.yaml",
    "grid:\n  detectors.min_repeat: [2, 3]\n  detectors.far_threshold_px: [80.0, 120.0]\n",
  )
  ledger = Ledger(tmp_path / "ledger.jsonl")
  config = LoopConfig(run_id="t", out_dir=tmp_path / "out")
  state = run_loop(
    baseline, grid_proposals(baseline, grid), DetectorExecutor(), eval_set, ledger,
    config, log=lambda *_: None,
  )
  assert state.n_kept >= 1
  assert state.best_candidate.detectors.min_repeat == 2
  assert state.best_scores.holdout.primary >= 0.9  # generalized to holdout
  best_file = tmp_path / "out" / "best" / "candidate.yaml"
  assert best_file.exists()

  # Ledger is append-only JSONL with verdicts.
  lines = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
  assert lines[0]["verdict"] == "baseline"
  assert any(rec["verdict"] == "kept" for rec in lines)
  assert all(rec["eval_set_hash"] == eval_set.content_hash for rec in lines)


def test_loop_dedupes_by_hash_across_sessions(tmp_path, eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  grid = _write(tmp_path / "grid.yaml", "grid:\n  detectors.min_repeat: [2, 3]\n")
  ledger_path = tmp_path / "ledger.jsonl"
  config = LoopConfig(run_id="t", out_dir=tmp_path / "out")

  run_loop(baseline, grid_proposals(baseline, grid), DetectorExecutor(), eval_set,
           Ledger(ledger_path), config, log=lambda *_: None)
  n_first = len(ledger_path.read_text().splitlines())
  # Second session, same grid: everything already tried -> no new entries.
  run_loop(baseline, grid_proposals(baseline, grid), DetectorExecutor(), eval_set,
           Ledger(ledger_path), config, log=lambda *_: None)
  assert len(ledger_path.read_text().splitlines()) == n_first


def test_loop_discards_regressions(tmp_path, eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  # far_threshold 5000: far misses stop being Location Hallucination -> worse.
  queue = _write(
    tmp_path / "q.yaml",
    "queue:\n  - name: worse\n    overrides:\n      detectors: {far_threshold_px: 5000.0}\n",
  )
  ledger = Ledger(tmp_path / "ledger.jsonl")
  config = LoopConfig(run_id="t", out_dir=tmp_path / "out")
  state = run_loop(baseline, queue_proposals(baseline, queue), DetectorExecutor(),
                   eval_set, ledger, config, log=lambda *_: None)
  assert state.n_kept == 0
  assert state.best_candidate.name == "baseline"


def test_max_experiments_cap(tmp_path, eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  grid = _write(
    tmp_path / "grid.yaml",
    "grid:\n  detectors.far_threshold_px: [60.0, 70.0, 80.0, 90.0, 100.0, 110.0]\n",
  )
  ledger = Ledger(tmp_path / "ledger.jsonl")
  config = LoopConfig(run_id="t", out_dir=tmp_path / "out", max_experiments=2)
  state = run_loop(baseline, grid_proposals(baseline, grid), DetectorExecutor(),
                   eval_set, ledger, config, log=lambda *_: None)
  assert len(state.records) <= 3  # baseline + 2


def test_summary_written_at_weekly_report_path(tmp_path, eval_set):
  baseline = candidate_from_dict({"name": "baseline"})
  grid = _write(tmp_path / "grid.yaml", "grid:\n  detectors.min_repeat: [2]\n")
  config = LoopConfig(run_id="run-42", out_dir=tmp_path / "out")
  state = run_loop(baseline, grid_proposals(baseline, grid), DetectorExecutor(),
                   eval_set, Ledger(tmp_path / "ledger.jsonl"), config,
                   log=lambda *_: None)
  path = write_summary(state, eval_set, config)
  assert path == tmp_path / "out" / "loop_outputs" / "run-42" / "summary.md"
  text = path.read_text()
  assert "macro-F1" in text and "not" in text.lower()  # provenance disclaimer present
