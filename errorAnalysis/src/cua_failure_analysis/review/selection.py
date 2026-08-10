"""Episode selection for taxonomy discovery review packets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from cua_failure_analysis.review.packet import (
  REPLAY_FAILED,
  REPLAY_GOLD,
  REPLAY_INCOMPLETE,
)

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


# Offline whole-trajectory judge outputs (trajectory_judge / osworld_traj_analysis)
# use their own agent-model naming in `uid`/`model`; map onto packet model slugs.
_OFFLINE_MODEL_SLUGS = {
  "opencua-3b": "a3b",
  "opencua-a3b": "a3b",
  "opencua_a3b": "a3b",
  "opencua-7b": "7b",
  "opencua_7b": "7b",
}
_OFFLINE_JUDGE_FIELDS = (
  "analysis",
  "category",
  "primary_failure_mode",
  "failing_step",
  "secondary_failure_modes",
  "confidence",
)


def load_offline_judge(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
  """``(model_slug, task_id) -> trimmed classification`` from a trajectory_judge
  classifications JSONL (``parse_ok`` rows only; unmapped agent models skipped)."""
  out: dict[tuple[str, str], dict[str, Any]] = {}
  for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      row = json.loads(line)
    except json.JSONDecodeError:
      continue
    if not row.get("parse_ok"):
      continue
    model = str(row.get("model") or str(row.get("uid") or "").split("/", 1)[0])
    slug = _OFFLINE_MODEL_SLUGS.get(model)
    task_id = row.get("task_id") or str(row.get("uid") or "").rsplit("/", 1)[-1]
    if slug is None or not task_id:
      continue
    cls = row.get("classification") or {}
    trimmed = {k: cls.get(k) for k in _OFFLINE_JUDGE_FIELDS}
    trimmed["num_steps"] = row.get("num_steps")
    out[(slug, task_id)] = trimmed
  return out


def load_task_domains(path: Path) -> dict[str, str]:
  """``task_id -> domain`` from a ``domain/task_id`` task list (all_tasks.txt).

  Needed for guided replays whose task is absent from the HF zips: their domain
  cannot be recovered from an episode id, and the gold manifest has no domain.
  """
  out: dict[str, str] = {}
  for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or "/" not in line:
      continue
    domain, task_id = line.split("/", 1)
    out[task_id.strip()] = domain.strip()
  return out


def select_paired_all_episodes(
  zip_paths: dict[str, Path],
  *,
  run_dirs: list[Path] | None = None,
  gold_root: Path | None = None,
  select_turns: dict[str, str] | None = None,
  model_order: tuple[str, ...] = ("a3b", "7b"),
  offline_judges: dict[str, dict[tuple[str, str], dict[str, Any]]] | None = None,
  task_domains: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  """Select EVERY task present in the zips (paired by ``task_id``), not just pilot.

  Judge metadata is merged from ``run_dirs`` when the episode was analyzed there.
  When ``gold_root`` is given, every guided replay under ``gold_root/<task_id>/``
  gets a third ``human`` trace (built from the replay directory, not a zip — see
  ``build_review_packet``), including replays that never produced a trace: those
  become ``replay_status: incomplete`` stubs carrying only the replay log, so the
  packet covers the whole sweep rather than silently dropping its failures.
  Replays whose task is absent from the zips become human-only rows; pass
  ``task_domains`` (see ``load_task_domains``) to give those rows a domain.
  ``offline_judges`` maps a judge name to a ``load_offline_judge`` result; matching
  classifications are attached to model episodes as ``episode["offline_judges"]``.
  """
  import zipfile

  from cua_failure_analysis.adapters.grouping import group_opencua_episodes

  select_turns = select_turns or {}
  run_dirs = run_dirs or []
  offline_judges = offline_judges or {}

  slug_to_run = {_model_slug(d): d for d in run_dirs}
  labels = {m: load_all_labels(slug_to_run[m]) if m in slug_to_run else {} for m in model_order}
  manifests = {m: load_manifest_by_task(slug_to_run[m]) if m in slug_to_run else {} for m in model_order}

  episodes_by_model: dict[str, dict[str, str]] = {}
  success_by_model: dict[str, dict[str, bool | None]] = {}
  for model in model_order:
    zip_path = zip_paths.get(model)
    if zip_path is None:
      raise ValueError(f"Missing zip path for model {model!r}")
    episodes_by_model[model] = {}
    success_by_model[model] = {}
    with zipfile.ZipFile(zip_path) as zf:
      for bundle in group_opencua_episodes(zf, select_turn=select_turns.get(model)):
        tid = _task_id(bundle.episode_id)
        episodes_by_model[model][tid] = bundle.episode_id
        result_member = next(
          (m for m in bundle.members if m.endswith("/result.txt")), None
        )
        success = None
        if result_member:
          try:
            raw = zf.read(result_member).decode("utf-8", "replace").strip()
            success = float(raw) >= 1.0 if raw else None
          except (ValueError, KeyError):
            success = None
        success_by_model[model][tid] = success

  task_domains = task_domains or {}
  task_domain: dict[str, str] = {}
  for eps in episodes_by_model.values():
    for tid, eid in eps.items():
      task_domain.setdefault(tid, _domain(eid))

  # Guided replays with no zip episode still get a (human-only) row.
  if gold_root is not None and gold_root.exists():
    for entry in sorted(gold_root.iterdir()):
      if entry.is_dir():
        task_domain.setdefault(entry.name, task_domains.get(entry.name, "unknown"))
  all_task_ids = sorted(task_domain, key=lambda t: (task_domain[t], t))

  episodes: list[dict[str, Any]] = []
  task_groups: list[dict[str, Any]] = []

  for task_id in all_task_ids:
    present = {m: episodes_by_model[m][task_id] for m in model_order if task_id in episodes_by_model[m]}

    gold_dir = (gold_root / task_id) if gold_root is not None else None
    has_gold_dir = bool(gold_dir and gold_dir.is_dir())
    has_trace = bool(gold_dir and (gold_dir / "trace.jsonl").exists())
    gold_manifest: dict[str, Any] = {}
    if gold_dir is not None:
      gm_path = gold_dir / "manifest.json"
      if gm_path.exists():
        gold_manifest = json.loads(gm_path.read_text(encoding="utf-8"))

    hrefs = {m: f"{m}/{eid.replace('/', '__')}/episode.html" for m, eid in present.items()}
    domain = _domain(next(iter(present.values()))) if present else task_domain[task_id]
    human_eid = f"{domain}/{task_id}"
    if has_gold_dir:
      hrefs["human"] = f"human/{human_eid.replace('/', '__')}/episode.html"

    group_models: dict[str, dict[str, Any]] = {}
    for model, eid in present.items():
      label_row = labels[model].get(eid)
      manifest_row = manifests[model].get(task_id)
      siblings = [
        {"href": h, "model": m} for m, h in hrefs.items() if m != model
      ]
      entry = _manifest_entry(
        model=model,
        run_dir=slug_to_run.get(model, Path(str(zip_paths[model]))),
        episode_id=eid,
        manifest_row=manifest_row,
        label_row=label_row,
        task_id=task_id,
        sibling_href=hrefs.get("7b" if model == "a3b" else "a3b"),
      )
      entry["siblings"] = siblings
      if not entry["instruction"]:
        entry["instruction"] = gold_manifest.get("instruction", "")
      if entry["success"] is None:
        entry["success"] = success_by_model[model].get(task_id)
      entry["offline_judges"] = {
        name: judge[(model, task_id)]
        for name, judge in offline_judges.items()
        if (model, task_id) in judge
      }
      episodes.append(entry)
      group_models[model] = {
        "href": hrefs[model],
        "episode_id": eid,
        "success": entry["success"],
        "provisional_primary": entry["provisional_primary"],
        "t_star": entry["t_star"],
        "offline": {
          name: cls.get("primary_failure_mode") or ""
          for name, cls in entry["offline_judges"].items()
        },
      }

    replay_status = ""
    if has_gold_dir:
      if not has_trace:
        replay_status = REPLAY_INCOMPLETE
      else:
        replay_status = REPLAY_GOLD if gold_manifest.get("success") else REPLAY_FAILED
      human_entry = {
        "model": "human",
        "episode_id": human_eid,
        "domain": domain,
        "task_id": task_id,
        "success": gold_manifest.get("success"),
        "t_star": None,
        "provisional_primary": "",
        "secondary_modes": [],
        "propagated": False,
        "evidence": "",
        "confidence": None,
        "tier_used": "",
        "run_dir": str(gold_dir),
        "gold_dir": str(gold_dir),
        "replay_status": replay_status,
        "confusing": False,
        "sibling_href": hrefs.get("a3b") or hrefs.get("7b"),
        "siblings": [{"href": h, "model": m} for m, h in hrefs.items() if m != "human"],
        "instruction": gold_manifest.get("instruction", ""),
      }
      episodes.append(human_entry)
      group_models["human"] = {
        "href": hrefs["human"],
        "episode_id": human_eid,
        "success": gold_manifest.get("success"),
        "provisional_primary": "",
        "t_star": None,
        "replay_status": replay_status,
      }

    judges_disagree = any(
      len({p for p in gm.get("offline", {}).values() if p}) > 1
      for gm in group_models.values()
    )
    task_groups.append(
      {
        "task_id": task_id,
        "domain": domain,
        "missing_models": [m for m in model_order if m not in present]
        + ([] if has_gold_dir else ["human"]),
        "models": group_models,
        "judges_disagree": judges_disagree,
        "replay_status": replay_status,
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
  label_batch: list[str] | None = None,
) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = {
    "packet_id": packet_id,
    "selection_mode": selection_mode,
    "n_episodes": len(episodes),
    "n_tasks": len(task_groups) if task_groups else None,
    "a3b_run": a3b_run,
    "7b_run": b7_run,
    "label_batch": label_batch or [],
    "task_groups": task_groups or [],
    "episodes": episodes,
  }
  path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
