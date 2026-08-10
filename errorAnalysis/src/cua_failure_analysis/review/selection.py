"""Episode selection for taxonomy discovery review packets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SUCCESS_CLAIM_RE = re.compile(
  r"\b(successfully|accomplished|terminate.*success|nothing more.*done|task.*complete)\b",
  re.I,
)


def load_pilot_task_ids(tasks_file: Path, *, phase: str = "pilot") -> list[str]:
  data = json.loads(tasks_file.read_text(encoding="utf-8"))
  if phase == "pilot":
    ids = data.get("pilot_task_ids")
    if ids:
      return list(ids)
  if phase == "core":
    return [t["task_id"] for t in data.get("tasks", []) if t.get("task_id")][:100]
  raise ValueError(f"Unknown phase {phase!r}")


def load_all_labels(run_dir: Path) -> dict[str, dict[str, Any]]:
  """Map ``episode_id`` -> label row (failed episodes only)."""
  labels_path = run_dir / "failure_labels.jsonl"
  if not labels_path.exists():
    return {}
  out: dict[str, dict[str, Any]] = {}
  with labels_path.open(encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      row = json.loads(line)
      eid = row.get("episode_id")
      if eid:
        out[eid] = row
  return out


def load_failed_labels(run_dir: Path) -> list[dict[str, Any]]:
  return [
    row
    for row in load_all_labels(run_dir).values()
    if row.get("status") == "failed" and row.get("primary_mode")
  ]


def load_manifest_by_task(run_dir: Path) -> dict[str, dict[str, Any]]:
  path = run_dir / "episode_manifests.json"
  if not path.exists():
    return {}
  rows = json.loads(path.read_text(encoding="utf-8"))
  by_task: dict[str, dict[str, Any]] = {}
  for row in rows:
    eid = row.get("episode_id", "")
    task_id = eid.split("/", 1)[1] if "/" in eid else row.get("task_id", "")
    if task_id:
      by_task[task_id] = row
  return by_task


def _domain(episode_id: str) -> str:
  return episode_id.split("/", 1)[0] if "/" in episode_id else "unknown"


def _task_id(episode_id: str) -> str:
  return episode_id.split("/", 1)[1] if "/" in episode_id else episode_id


def is_confusing_episode(row: dict[str, Any]) -> bool:
  primary = row.get("primary_mode", "")
  secondaries = set(row.get("secondary_modes") or [])
  evidence = str(row.get("evidence") or "")
  if primary == "Reasoning Drift" and "Goal Hallucination" in secondaries:
    return True
  if primary == "Action Looping (Repetition)" and not row.get("propagated"):
    return True
  if SUCCESS_CLAIM_RE.search(evidence):
    return True
  if primary == "Goal Hallucination" and "Reasoning Drift" in secondaries:
    return True
  return False


def _model_slug(run_dir: Path) -> str:
  meta_path = run_dir / "run_metadata.json"
  if meta_path.exists():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    model_id = str(meta.get("model_id") or "")
    if "7b" in model_id.lower():
      return "7b"
    if "a3b" in model_id.lower():
      return "a3b"
    package = str(meta.get("package") or "")
    if "7b" in package.lower():
      return "7b"
    if "a3b" in package.lower():
      return "a3b"
  name = run_dir.name.lower()
  if "7b" in name:
    return "7b"
  if "a3b" in name:
    return "a3b"
  return run_dir.name


def _manifest_entry(
  *,
  model: str,
  run_dir: Path,
  episode_id: str,
  manifest_row: dict[str, Any] | None,
  label_row: dict[str, Any] | None,
  task_id: str,
  sibling_href: str | None = None,
) -> dict[str, Any]:
  success = None
  if manifest_row is not None:
    success = manifest_row.get("success")
  if label_row is not None:
    success = label_row.get("success", success)

  confusing = bool(label_row and is_confusing_episode(label_row))
  return {
    "model": model,
    "episode_id": episode_id,
    "domain": _domain(episode_id),
    "task_id": task_id,
    "success": success,
    "t_star": label_row.get("t_star") if label_row else None,
    "provisional_primary": label_row.get("primary_mode") if label_row else "",
    "secondary_modes": list(label_row.get("secondary_modes") or []) if label_row else [],
    "propagated": bool(label_row.get("propagated")) if label_row else False,
    "evidence": label_row.get("evidence", "") if label_row else "",
    "confidence": label_row.get("confidence") if label_row else None,
    "tier_used": label_row.get("tier_used", "") if label_row else "",
    "run_dir": str(run_dir),
    "confusing": confusing,
    "sibling_href": sibling_href,
    "instruction": (manifest_row or {}).get("instruction", ""),
  }


def select_paired_pilot_episodes(
  run_dirs: list[Path],
  *,
  tasks_file: Path,
  phase: str = "pilot",
  model_order: tuple[str, ...] = ("a3b", "7b"),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  """Select all pilot tasks with both models' traces (paired by ``task_id``).

  Returns ``(episodes, task_groups)`` where ``task_groups`` holds index metadata.
  """
  task_ids = load_pilot_task_ids(tasks_file, phase=phase)
  if len(run_dirs) != 2:
    raise ValueError("select_paired_pilot_episodes expects exactly two run dirs")

  slug_to_dir = {_model_slug(d): d for d in run_dirs}
  missing_models = [m for m in model_order if m not in slug_to_dir]
  if missing_models:
    raise ValueError(f"Missing run dirs for models: {missing_models}")

  manifests = {m: load_manifest_by_task(slug_to_dir[m]) for m in model_order}
  labels = {m: load_all_labels(slug_to_dir[m]) for m in model_order}

  episodes: list[dict[str, Any]] = []
  task_groups: list[dict[str, Any]] = []

  for task_id in task_ids:
    group_entries: dict[str, dict[str, Any]] = {}
    for model in model_order:
      run_dir = slug_to_dir[model]
      manifest_row = manifests[model].get(task_id)
      if manifest_row is None:
        continue
      episode_id = manifest_row["episode_id"]
      label_row = labels[model].get(episode_id)
      group_entries[model] = {
        "manifest_row": manifest_row,
        "label_row": label_row,
        "episode_id": episode_id,
        "run_dir": run_dir,
      }

    if len(group_entries) < len(model_order):
      present = set(group_entries)
      task_groups.append(
        {
          "task_id": task_id,
          "domain": _domain(next(iter(group_entries.values()))["episode_id"]),
          "missing_models": [m for m in model_order if m not in present],
          "models": {},
        }
      )
      continue

    hrefs: dict[str, str] = {}
    for model, info in group_entries.items():
      eid = info["episode_id"]
      hrefs[model] = f"{model}/{eid.replace('/', '__')}/episode.html"

    for model in model_order:
      info = group_entries[model]
      other = model_order[1] if model == model_order[0] else model_order[0]
      sibling = hrefs.get(other)
      episodes.append(
        _manifest_entry(
          model=model,
          run_dir=info["run_dir"],
          episode_id=info["episode_id"],
          manifest_row=info["manifest_row"],
          label_row=info["label_row"],
          task_id=task_id,
          sibling_href=sibling,
        )
      )

    task_groups.append(
      {
        "task_id": task_id,
        "domain": _domain(group_entries[model_order[0]]["episode_id"]),
        "missing_models": [],
        "models": {
          m: {
            "href": hrefs[m],
            "episode_id": group_entries[m]["episode_id"],
            "success": group_entries[m]["manifest_row"].get("success"),
            "provisional_primary": (group_entries[m]["label_row"] or {}).get("primary_mode", ""),
            "t_star": (group_entries[m]["label_row"] or {}).get("t_star"),
          }
          for m in model_order
        },
      }
    )

  return episodes, task_groups


def select_from_pool(
  rows: list[dict[str, Any]],
  *,
  model: str,
  run_dir: Path,
  n: int = 10,
  confusing_slots: int = 3,
) -> list[dict[str, Any]]:
  if not rows:
    return []

  confusing = [r for r in rows if is_confusing_episode(r)]
  confusing.sort(key=lambda r: r.get("episode_id", ""))

  selected_ids: set[str] = set()
  selected: list[dict[str, Any]] = []

  def add(row: dict[str, Any]) -> bool:
    eid = row["episode_id"]
    if eid in selected_ids:
      return False
    selected_ids.add(eid)
    selected.append(
      _manifest_entry(
        model=model,
        run_dir=run_dir,
        episode_id=eid,
        manifest_row=None,
        label_row=row,
        task_id=_task_id(eid),
      )
    )
    return True

  for row in confusing[:confusing_slots]:
    add(row)

  by_leaf: dict[str, list[dict[str, Any]]] = defaultdict(list)
  for row in rows:
    if row["episode_id"] not in selected_ids:
      by_leaf[row["primary_mode"]].append(row)
  for leaf_rows in by_leaf.values():
    leaf_rows.sort(key=lambda r: (_domain(r["episode_id"]), r.get("episode_id", "")))

  leaves = sorted(by_leaf)
  cursor = {leaf: 0 for leaf in leaves}
  while len(selected) < n:
    progressed = False
    for leaf in leaves:
      pool = by_leaf[leaf]
      while cursor[leaf] < len(pool):
        row = pool[cursor[leaf]]
        cursor[leaf] += 1
        if add(row):
          progressed = True
          break
      if len(selected) >= n:
        break
    if not progressed:
      break

  return selected[:n]


def select_review_episodes(
  run_dirs: list[Path],
  *,
  n_per_model: int = 10,
  confusing_slots: int = 3,
  mode: str = "paired-pilot",
  tasks_file: Path | None = None,
  phase: str = "pilot",
) -> list[dict[str, Any]]:
  if mode == "paired-pilot":
    if tasks_file is None:
      raise ValueError("tasks_file required for paired-pilot mode")
    episodes, _groups = select_paired_pilot_episodes(
      run_dirs, tasks_file=tasks_file, phase=phase
    )
    return episodes

  all_selected: list[dict[str, Any]] = []
  for run_dir in run_dirs:
    rows = load_failed_labels(run_dir)
    model = _model_slug(run_dir)
    picked = select_from_pool(
      rows,
      model=model,
      run_dir=run_dir,
      n=n_per_model,
      confusing_slots=confusing_slots,
    )
    all_selected.extend(picked)
  return all_selected


def write_manifest(
  path: Path,
  episodes: list[dict[str, Any]],
  *,
  packet_id: str,
  a3b_run: str | None = None,
  b7_run: str | None = None,
  task_groups: list[dict[str, Any]] | None = None,
  selection_mode: str = "paired-pilot",
) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = {
    "packet_id": packet_id,
    "selection_mode": selection_mode,
    "n_episodes": len(episodes),
    "n_tasks": len(task_groups) if task_groups else None,
    "a3b_run": a3b_run,
    "7b_run": b7_run,
    "task_groups": task_groups or [],
    "episodes": episodes,
  }
  path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
