"""The keep/discard loop with an append-only ledger.

Mechanics (scoping doc §5): propose → dedupe by hash → evaluate on the frozen
eval set → score → append ledger entry → keep iff calibration primary metric
improves by >= min_delta. Holdout is scored and recorded but NEVER used for
keep/discard; a kept candidate that regresses holdout is flagged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from auto_research.candidates import Candidate, save_candidate
from auto_research.objective import EvalSet, Scores, score_predictions


@dataclass
class LoopConfig:
  min_delta: float = 0.005
  overfit_epsilon: float = 0.05
  max_experiments: int = 200
  run_id: str = "dev"
  out_dir: Path = Path("data")


@dataclass
class ExperimentRecord:
  experiment_id: str
  run_id: str
  candidate_name: str
  candidate_hash: str
  parent_hash: str | None
  executor: str
  eval_set_hash: str
  scores: dict
  primary_calibration: float
  primary_holdout: float
  delta_vs_best: float
  verdict: str
  notes: str = ""
  cost_usd: float = 0.0
  timestamp: str = ""

  def as_dict(self) -> dict:
    return dict(self.__dict__)


@dataclass
class LoopState:
  best_candidate: Candidate
  best_scores: Scores
  records: list[ExperimentRecord] = field(default_factory=list)
  n_kept: int = 0
  n_discarded: int = 0


def _now() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Ledger:
  """Append-only JSONL ledger; also knows which hashes were already tried."""

  def __init__(self, path: Path) -> None:
    self.path = path
    self.path.parent.mkdir(parents=True, exist_ok=True)
    self.seen_hashes: set[str] = set()
    if self.path.exists():
      for line in self.path.read_text(encoding="utf-8").splitlines():
        if line.strip():
          try:
            self.seen_hashes.add(json.loads(line).get("candidate_hash", ""))
          except json.JSONDecodeError:
            continue

  def append(self, record: ExperimentRecord) -> None:
    with self.path.open("a", encoding="utf-8") as f:
      f.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")
    self.seen_hashes.add(record.candidate_hash)

  def tail(self, n: int = 20) -> list[dict]:
    if not self.path.exists():
      return []
    lines = [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines[-n:]]


def evaluate_candidate(candidate: Candidate, executor, eval_set: EvalSet) -> Scores:
  predictions = executor.run(candidate, eval_set)
  return score_predictions(eval_set, predictions)


def run_loop(
  baseline: Candidate,
  proposals: Iterable[Candidate],
  executor,
  eval_set: EvalSet,
  ledger: Ledger,
  config: LoopConfig,
  meter=None,
  log=print,
) -> LoopState:
  exp_index = len(ledger.seen_hashes)

  def record_for(candidate: Candidate, scores: Scores, delta: float, verdict: str,
                 parent: str | None) -> ExperimentRecord:
    nonlocal exp_index
    rec = ExperimentRecord(
      experiment_id=f"exp-{exp_index:04d}",
      run_id=config.run_id,
      candidate_name=candidate.name,
      candidate_hash=candidate.content_hash(),
      parent_hash=parent,
      executor=getattr(executor, "name", type(executor).__name__),
      eval_set_hash=eval_set.content_hash,
      scores=scores.as_dict(),
      primary_calibration=round(scores.calibration.primary, 4),
      primary_holdout=round(scores.holdout.primary, 4),
      delta_vs_best=round(delta, 4),
      verdict=verdict,
      notes=candidate.notes,
      cost_usd=round(getattr(meter, "spent_usd", 0.0), 4),
      timestamp=_now(),
    )
    exp_index += 1
    return rec

  # Baseline first (skip if already in ledger from a previous session).
  base_hash = baseline.content_hash()
  base_scores = evaluate_candidate(baseline, executor, eval_set)
  state = LoopState(best_candidate=baseline, best_scores=base_scores)
  if base_hash not in ledger.seen_hashes:
    rec = record_for(baseline, base_scores, 0.0, "baseline", None)
    ledger.append(rec)
    state.records.append(rec)
  log(
    f"[baseline] {baseline.name}: calibration {base_scores.calibration.primary:.4f} "
    f"holdout {base_scores.holdout.primary:.4f}"
  )

  n_run = 0
  for candidate in proposals:
    if n_run >= config.max_experiments:
      log(f"[stop] max_experiments={config.max_experiments} reached")
      break
    cand_hash = candidate.content_hash()
    if cand_hash in ledger.seen_hashes:
      continue
    n_run += 1
    scores = evaluate_candidate(candidate, executor, eval_set)
    delta = scores.calibration.primary - state.best_scores.calibration.primary
    kept = delta >= config.min_delta
    verdict = "kept" if kept else "discarded"
    if kept and scores.holdout.primary < state.best_scores.holdout.primary - config.overfit_epsilon:
      verdict = "kept_suspect_overfit"
    rec = record_for(candidate, scores, delta,
                     verdict, parent=state.best_candidate.content_hash())
    ledger.append(rec)
    state.records.append(rec)
    log(
      f"[{rec.experiment_id}] {candidate.name}: calib {scores.calibration.primary:.4f} "
      f"(Δ{delta:+.4f}) holdout {scores.holdout.primary:.4f} → {verdict}"
    )
    if kept:
      state.best_candidate = candidate
      state.best_scores = scores
      state.n_kept += 1
      best_path = config.out_dir / "best" / "candidate.yaml"
      save_candidate(candidate, best_path)
    else:
      state.n_discarded += 1

  return state


def write_summary(state: LoopState, eval_set: EvalSet, config: LoopConfig,
                  meter=None) -> Path:
  """Compact run summary at the path ops/weekly_report.py scans."""
  out = config.out_dir / "loop_outputs" / config.run_id / "summary.md"
  out.parent.mkdir(parents=True, exist_ok=True)
  best = state.best_candidate
  lines = [
    f"# autoResearch loop run `{config.run_id}`",
    "",
    f"- Completed: {_now()}",
    f"- Eval set hash: `{eval_set.content_hash}` "
    f"({len(eval_set.split('calibration'))} calibration / {len(eval_set.split('holdout'))} holdout cases)",
    f"- Experiments this session: {len(state.records)} "
    f"(kept {state.n_kept}, discarded {state.n_discarded})",
    f"- Best candidate: **{best.name}** (`{best.content_hash()}`)",
    f"- Best calibration {state.best_scores.calibration.primary:.4f} / "
    f"holdout {state.best_scores.holdout.primary:.4f} (macro-F1, multi-label)",
  ]
  if meter is not None:
    lines.append(f"- Cost: ${meter.spent_usd:.2f} of ${meter.cap_usd:.2f} cap ({meter.calls} calls)")
  else:
    lines.append("- Cost: $0.00 (offline detector executor)")
  lines += [
    "",
    "## Kept candidates",
    "",
  ]
  kept = [r for r in state.records if r.verdict.startswith("kept")]
  if kept:
    for r in kept:
      lines.append(
        f"- `{r.experiment_id}` {r.candidate_name}: calib {r.primary_calibration:.4f} "
        f"(Δ{r.delta_vs_best:+.4f}), holdout {r.primary_holdout:.4f} [{r.verdict}]"
        + (f" — {r.notes}" if r.notes else "")
      )
  else:
    lines.append("- none (baseline stands)")
  lines += [
    "",
    "_Scores are harness-calibration numbers on the pinned eval set — not "
    "scientific results. See autoResearch/AGENTS.md boundaries._",
    "",
  ]
  out.write_text("\n".join(lines), encoding="utf-8")
  return out
