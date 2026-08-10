"""Proposal sources: where candidate mutations come from.

P0 ``grid``: enumerated parameter grid (no LLM, deterministic, CI-safe).
P1 ``queue``: human/agent-authored YAML queue of candidate overrides.
P2 ``llm``: an LLM proposer reading program.md + the ledger tail — gated
   behind an explicit flag because it spends money and acts autonomously
   (approval per docs/multi_idea_stages.md roadmap).
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Iterator

import yaml

from auto_research.candidates import Candidate, apply_overrides

MAX_GRID = 500


def grid_proposals(base: Candidate, grid_path: Path) -> Iterator[Candidate]:
  """Yield candidates from a cartesian grid spec.

  YAML shape (dotted keys into the candidate schema):
    grid:
      detectors.min_repeat: [2, 3]
      detectors.far_threshold_px: [40, 80, 120]
  """
  spec = yaml.safe_load(grid_path.read_text(encoding="utf-8")) or {}
  grid: dict[str, list] = spec.get("grid", {})
  if not grid:
    return
  keys = sorted(grid)
  combos = list(itertools.product(*(grid[k] for k in keys)))
  if len(combos) > MAX_GRID:
    raise ValueError(f"Grid too large ({len(combos)} > {MAX_GRID}); shrink it.")
  for i, combo in enumerate(combos):
    overrides: dict = {}
    for key, value in zip(keys, combo):
      section, _, leaf = key.partition(".")
      if not leaf:
        overrides[section] = value
      else:
        overrides.setdefault(section, {})[leaf] = value
    label_bits = ",".join(f"{k.split('.')[-1]}={v}" for k, v in zip(keys, combo))
    yield apply_overrides(base, overrides, name=f"grid-{i:04d}[{label_bits}]")


def queue_proposals(base: Candidate, queue_path: Path) -> Iterator[Candidate]:
  """Yield candidates from an authored queue file.

  YAML shape:
    queue:
      - name: wider-near-margin
        notes: judge misses near-misses; widen margin
        overrides:
          detectors: {near_margin_ratio: 2.5}
  """
  spec = yaml.safe_load(queue_path.read_text(encoding="utf-8")) or {}
  for i, item in enumerate(spec.get("queue", [])):
    name = item.get("name") or f"queue-{i:04d}"
    cand = apply_overrides(base, item.get("overrides", {}) or {}, name=name)
    if item.get("notes"):
      cand.notes = str(item["notes"])
    yield cand


PROPOSER_SYSTEM = """You are the proposal engine of an autoresearch loop for a
computer-use-agent failure-analysis project. You mutate ONE candidate config
(judge/detector parameters) at a time to improve agreement with human gold
labels (primary metric: multi-label macro-F1 on the calibration split).

Read the directives and the experiment ledger, then output STRICT JSON:
{"name": "<short-slug>", "notes": "<one-line hypothesis>",
 "overrides": {"detectors": {...}, "judge": {...}}}

Rules: change at most 2 parameters per proposal; never propose parameters
outside the documented schema; never touch the eval set, taxonomy, or metric.
"""


def llm_proposals(
  base: Candidate,
  program_md: Path,
  ledger_tail: list[dict],
  max_proposals: int = 10,
  complete_fn=None,
) -> Iterator[Candidate]:
  """LLM proposer (P2). ``complete_fn(system, user) -> str`` does the call;
  defaults to ops/llm_client (Anthropic) resolved at repo root. Kept
  injectable so tests never hit the network.
  """
  if complete_fn is None:
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "ops"))
    import llm_client  # type: ignore

    cfg = llm_client.llm_config()
    if cfg is None:
      raise RuntimeError(
        "LLM proposer needs ANTHROPIC_API_KEY (or ops/config/meetings.env). "
        "Use --proposals grid/queue offline."
      )

    def complete_fn(system: str, user: str) -> str:  # type: ignore[misc]
      return llm_client.complete(cfg, system, user, max_tokens=1024)

  directives = program_md.read_text(encoding="utf-8") if program_md.exists() else ""
  for i in range(max_proposals):
    user = (
      f"## Directives\n{directives}\n\n"
      f"## Current base candidate\n{json.dumps(base.as_dict(), indent=1)}\n\n"
      f"## Ledger tail (most recent last)\n"
      + "\n".join(json.dumps(e) for e in ledger_tail[-20:])
      + f"\n\nPropose experiment #{i + 1}. STRICT JSON only."
    )
    raw = complete_fn(PROPOSER_SYSTEM, user).strip()
    if raw.startswith("```"):
      raw = raw.split("```")[1]
      if raw.startswith("json"):
        raw = raw[4:]
    try:
      spec = json.loads(raw)
      cand = apply_overrides(
        base, spec.get("overrides", {}) or {}, name=spec.get("name") or f"llm-{i:04d}"
      )
      cand.notes = str(spec.get("notes", ""))
    except (json.JSONDecodeError, ValueError, TypeError):
      continue  # malformed proposal: skip, never crash the loop
    yield cand
    ledger_tail = ledger_tail + [{"proposed": cand.name}]
