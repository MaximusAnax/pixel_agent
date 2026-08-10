"""Select the judge-calibration task slice (PROJECT_STATE action item).

Target slice: tasks where
  1. the Human Agent run succeeded,
  2. every listed agent model (default OpenCUA-3B and OpenCUA-7B) failed, and
  3. the judge produced a resolved failure-mode conclusion for at least one
     of those failed agent runs.

Inputs are plain run records so this works on manifests, attributions.jsonl,
or HF-trajectory summaries alike:
  {"task_id", "model_id", "success": bool, "judge_primary_mode": str | None}
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from cua_failure_analysis.labeling.multilabel import _is_unresolved


def _norm_model(model_id: str) -> str:
  return model_id.strip().lower().replace("_", "-")


def select_calibration_tasks(
  runs: list[dict],
  human_model: str = "human",
  agent_models: tuple[str, ...] = ("opencua-3b", "opencua-7b"),
  require_judge_conclusion: bool = True,
  limit: int = 5,
) -> list[str]:
  """Return up to ``limit`` task_ids matching the calibration slice, sorted."""
  agent_set = {_norm_model(m) for m in agent_models}
  human = _norm_model(human_model)

  by_task: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
  for run in runs:
    if "task_id" not in run or "model_id" not in run:
      continue
    by_task[str(run["task_id"])][_norm_model(str(run["model_id"]))].append(run)

  selected: list[str] = []
  for task_id in sorted(by_task):
    models = by_task[task_id]
    human_runs = models.get(human, [])
    if not any(r.get("success") is True for r in human_runs):
      continue
    if not agent_set.issubset(models.keys()):
      continue
    if any(
      any(r.get("success") is True for r in models[m]) for m in agent_set
    ):
      continue
    if require_judge_conclusion:
      concluded = any(
        not _is_unresolved(str(r.get("judge_primary_mode") or ""))
        for m in agent_set
        for r in models[m]
      )
      if not concluded:
        continue
    selected.append(task_id)

  return selected[:limit]


def load_runs_from_attributions(
  attributions_path: Path,
  manifests_root: Path | None = None,
) -> list[dict]:
  """Assemble run records from attributions.jsonl plus trace manifests.

  Attribution records carry trace_path + judge output; the sibling
  manifest.json supplies model_id and success. Records missing a manifest are
  skipped (they cannot satisfy the slice conditions anyway).
  """
  import json

  runs: list[dict] = []
  with attributions_path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      rec = json.loads(line)
      trace_path = Path(rec.get("trace_path", ""))
      manifest_path = trace_path.parent / "manifest.json"
      if manifests_root is not None and not manifest_path.is_absolute():
        manifest_path = manifests_root / manifest_path
      if not manifest_path.exists():
        continue
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
      runs.append(
        {
          "task_id": manifest.get("task_id"),
          "model_id": manifest.get("model_id"),
          "success": manifest.get("success"),
          "judge_primary_mode": rec.get("primary_mode"),
        }
      )
  return runs
