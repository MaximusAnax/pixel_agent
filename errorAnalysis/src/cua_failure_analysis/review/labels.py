"""Merge human review labels with packet manifest for worksheet export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def judge_modes_ordered(ep: dict[str, Any]) -> list[str]:
  # All-applicable policy (2026-08-10): judge output carries an explicit
  # modes_ordered list (most-central-first). Prefer it when present.
  modes: list[str] = []
  for m in ep.get("modes_ordered") or ep.get("judge_modes_ordered") or []:
    if m and str(m) not in modes:
      modes.append(str(m))
  if modes:
    return modes
  # Legacy one-primary records: derive the ordered list.
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


def _format_mode_reasons(reasons: Any) -> str:
  if not isinstance(reasons, dict) or not reasons:
    return ""
  parts = []
  for key, val in reasons.items():
    text = str(val or "").replace("|", "/").replace("\n", " ").strip()
    parts.append(f"{key}={text}")
  return " | ".join(parts)


def _annotator_export_fields(
  human: dict[str, Any] | None,
  *,
  prefix: str,
) -> dict[str, str]:
  human_modes = list((human or {}).get("modes_ordered") or [])
  return {
    f"{prefix}_modes_ordered": human_modes_to_csv(human_modes),
    f"{prefix}_primary": human_modes[0] if human_modes else "",
    f"{prefix}_root_step": str(
      (human or {}).get("root_step") if (human or {}).get("root_step") is not None else ""
    ),
    f"{prefix}_reasoning": str((human or {}).get("reasoning") or ""),
    f"{prefix}_mode_reasons": _format_mode_reasons((human or {}).get("mode_reasons")),
    f"{prefix}_confidence": str(
      (human or {}).get("confidence") if (human or {}).get("confidence") is not None else ""
    ),
    f"{prefix}_is_propagated": str(bool((human or {}).get("is_propagated"))),
  }


def build_comparison_row(
  ep: dict[str, Any],
  *,
  human_a: dict[str, Any] | None,
  human_b: dict[str, Any] | None,
  annotator_a: str,
  annotator_b: str,
  columns: list[str],
) -> dict[str, str]:
  """Wide export row: judge + two annotators."""
  base = build_discovery_row(ep, human_a, columns=columns)
  judge_modes = judge_modes_ordered(ep)
  base["judge_label"] = judge_modes[0] if judge_modes else ""
  base.update(_annotator_export_fields(human_a, prefix=annotator_a))
  base.update(_annotator_export_fields(human_b, prefix=annotator_b))
  return {col: str(base.get(col, "")) for col in columns}


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
      "mode_reasons": _format_mode_reasons((human or {}).get("mode_reasons")),
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
      "oracle_status": str(ep.get("oracle_status") or ""),
    }
  )
  return {col: str(row.get(col, "")) for col in columns}
