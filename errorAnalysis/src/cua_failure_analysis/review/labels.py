"""Merge human review labels with packet manifest for worksheet export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def judge_modes_ordered(ep: dict[str, Any]) -> list[str]:
  modes: list[str] = []
  primary = ep.get("provisional_primary") or ep.get("judge_primary")
  if primary:
    modes.append(str(primary))
  for sec in ep.get("secondary_modes") or []:
    if sec and sec not in modes:
      modes.append(str(sec))
  return modes


def load_human_labels(path: Path | None) -> dict[str, dict[str, Any]]:
  if path is None or not path.exists():
    return {}
  data = json.loads(path.read_text(encoding="utf-8"))
  if isinstance(data, dict) and "labels" in data:
    return dict(data["labels"])
  if isinstance(data, dict):
    return data
  return {}


def label_storage_key(model: str, episode_id: str) -> str:
  return f"{model}/{episode_id.replace('/', '__')}"


def human_modes_to_csv(modes: list[str] | None) -> str:
  if not modes:
    return ""
  return ";".join(modes)


def build_discovery_row(
  ep: dict[str, Any],
  human: dict[str, Any] | None,
  *,
  columns: list[str],
) -> dict[str, str]:
  episode_id = ep["episode_id"]
  task_id = ep.get("task_id") or episode_id.split("/", 1)[-1]
  model = ep.get("model", "")
  trace_id = episode_id.replace("/", "__")
  judge_modes = judge_modes_ordered(ep)
  human_modes = list((human or {}).get("modes_ordered") or [])

  row = {col: "" for col in columns}
  row.update(
    {
      "trace_id": trace_id,
      "task_id": task_id,
      "seed": "0",
      "model": model,
      "episode_id": episode_id,
      "domain": ep.get("domain", ""),
      "episode_html": ep.get("episode_html") or f"{model}/{trace_id}/episode.html",
      "sibling_href": ep.get("sibling_href", ""),
      # Judge / pipeline (frozen at packet build)
      "judge_t_star": str(ep.get("t_star") if ep.get("t_star") is not None else ""),
      "judge_modes_ordered": human_modes_to_csv(judge_modes),
      "judge_reasoning": str(ep.get("evidence") or ""),
      "judge_confidence": str(ep.get("confidence") if ep.get("confidence") is not None else ""),
      "judge_label": judge_modes[0] if judge_modes else "",
      "t_star": str(ep.get("t_star") if ep.get("t_star") is not None else ""),
      "secondary_modes": ";".join(ep.get("secondary_modes") or []),
      "propagated": str(bool(ep.get("propagated"))),
      "provisional_primary": str(ep.get("provisional_primary") or ""),
      "provisional_evidence": str(ep.get("evidence") or ""),
      "tier_used": str(ep.get("tier_used") or ""),
      # Human (from human_labels.json)
      "reviewer": str((human or {}).get("reviewer") or ""),
      "root_step": str((human or {}).get("root_step") if (human or {}).get("root_step") is not None else ""),
      "human_modes_ordered": human_modes_to_csv(human_modes),
      "primary_revised": human_modes[0] if human_modes else "",
      "secondary_revised": human_modes_to_csv(human_modes[1:]),
      "human_reasoning": str((human or {}).get("reasoning") or ""),
      "human_confidence": str((human or {}).get("confidence") if (human or {}).get("confidence") is not None else ""),
      "is_propagated": str(bool((human or {}).get("is_propagated"))),
      "propagated_from_step": str(
        (human or {}).get("propagated_from_step")
        if (human or {}).get("propagated_from_step") is not None
        else ""
      ),
      "evaluator_mismatch": str(bool((human or {}).get("evaluator_mismatch"))),
      "taxonomy_issue": str((human or {}).get("taxonomy_issue") or ""),
      "candidate_new_leaf": str((human or {}).get("candidate_new_leaf") or ""),
      "notes": str((human or {}).get("notes") or ""),
    }
  )
  return {col: str(row.get(col, "")) for col in columns}
