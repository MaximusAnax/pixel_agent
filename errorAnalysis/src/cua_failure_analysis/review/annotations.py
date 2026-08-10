"""Multi-annotator review labels (schema v3) with v1/v2 migration."""

from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTERED_ANNOTATORS: tuple[str, ...] = ("abdoul", "raghav")
ANNOTATIONS_FILENAME = "annotations.json"
LEGACY_LABELS_FILENAME = "human_labels.json"
SCHEMA_VERSION = 3

# Why a *guided replay* failed to reach gold — a data-quality judgement about
# our own gold pipeline, deliberately NOT the agent failure taxonomy in
# failureTaxonomy.md (which is frozen and needs Abdoul's sign-off to change).
# Ported from the standalone gold audit viewer.
REPLAY_AUDIT_CATEGORIES: tuple[str, ...] = (
  "ui-drift",
  "grounding-miss",
  "human-steps-wrong",
  "evaluator-strict",
  "setup-fail",
  "timeout",
  "infra",
  "infeasible-ok",
  "unsure",
)


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_annotations(packet_id: str) -> dict[str, Any]:
  return {
    "schema_version": SCHEMA_VERSION,
    "packet_id": packet_id,
    "annotators": {
      annotator_id: {"labels": {}, "replay_audit": {}}
      for annotator_id in REGISTERED_ANNOTATORS
    },
  }


def validate_annotator_id(annotator_id: str) -> str:
  if annotator_id not in REGISTERED_ANNOTATORS:
    allowed = ", ".join(REGISTERED_ANNOTATORS)
    raise ValueError(f"Unknown annotator {annotator_id!r}; expected one of: {allowed}")
  return annotator_id


def migrate_v1_to_v2(data: dict[str, Any], packet_id: str) -> dict[str, Any]:
  """Convert legacy human_labels.json (v1) into current-schema annotations."""
  out = empty_annotations(packet_id)
  legacy_labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}
  reviewer = str(data.get("reviewer") or "").strip().lower()
  target = reviewer if reviewer in REGISTERED_ANNOTATORS else REGISTERED_ANNOTATORS[0]
  out["annotators"][target]["labels"] = dict(legacy_labels)
  return out


def normalize_annotations(data: dict[str, Any], *, packet_id: str) -> dict[str, Any]:
  version = data.get("schema_version")
  if version == 1 or ("labels" in data and "annotators" not in data):
    return migrate_v1_to_v2(data, packet_id)
  # v2 -> v3 is additive (replay_audit); v2 files upgrade on read.
  if version not in (2, SCHEMA_VERSION):
    raise ValueError(f"Unsupported annotations schema_version: {version!r}")

  out = empty_annotations(packet_id)
  out["packet_id"] = str(data.get("packet_id") or packet_id)
  annotators = data.get("annotators")
  if not isinstance(annotators, dict):
    return out

  for annotator_id in REGISTERED_ANNOTATORS:
    block = annotators.get(annotator_id) or {}
    if not isinstance(block, dict):
      continue
    labels = block.get("labels")
    if isinstance(labels, dict):
      out["annotators"][annotator_id]["labels"] = dict(labels)
    audit = block.get("replay_audit")
    if isinstance(audit, dict):
      out["annotators"][annotator_id]["replay_audit"] = dict(audit)
  return out


def _resolve_path(path: Path | None, packet_dir: Path | None) -> Path | None:
  if path is not None:
    return path
  if packet_dir is None:
    return None
  ann = packet_dir / ANNOTATIONS_FILENAME
  if ann.exists():
    return ann
  legacy = packet_dir / LEGACY_LABELS_FILENAME
  return legacy if legacy.exists() else ann


def load_annotations(
  path: Path | None,
  *,
  packet_id: str = "",
  packet_dir: Path | None = None,
) -> dict[str, Any]:
  resolved = _resolve_path(path, packet_dir)
  if resolved is None or not resolved.exists():
    return empty_annotations(packet_id)

  data = json.loads(resolved.read_text(encoding="utf-8"))
  if not isinstance(data, dict):
    raise ValueError(f"Invalid annotations file: {resolved}")
  pid = packet_id or str(data.get("packet_id") or (packet_dir.name if packet_dir else ""))
  return normalize_annotations(data, packet_id=pid)


@contextlib.contextmanager
def annotations_lock(path: Path):
  """Best-effort exclusive lock so two annotators saving into the same shared
  annotations.json (e.g. from different Babel nodes) cannot interleave the
  read-modify-write and clobber each other's namespace."""
  lock_path = path.parent / f".{path.name}.lock"
  try:
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as fh:
      try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield
      finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
  except (ImportError, OSError):
    yield


def save_annotations(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
  tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
  os.replace(tmp, path)


def list_annotators(data: dict[str, Any]) -> list[str]:
  annotators = data.get("annotators")
  if not isinstance(annotators, dict):
    return []
  return [aid for aid in REGISTERED_ANNOTATORS if aid in annotators]


def get_annotator_labels(data: dict[str, Any], annotator_id: str) -> dict[str, dict[str, Any]]:
  validate_annotator_id(annotator_id)
  block = (data.get("annotators") or {}).get(annotator_id) or {}
  labels = block.get("labels") if isinstance(block, dict) else {}
  return dict(labels) if isinstance(labels, dict) else {}


def get_replay_audit(data: dict[str, Any], annotator_id: str) -> dict[str, dict[str, Any]]:
  """One annotator's replay-audit notes, keyed by gold task_id."""
  validate_annotator_id(annotator_id)
  block = (data.get("annotators") or {}).get(annotator_id) or {}
  audit = block.get("replay_audit") if isinstance(block, dict) else {}
  return dict(audit) if isinstance(audit, dict) else {}


def validate_replay_category(category: str) -> str:
  """Empty clears the note's category; anything else must be a known tag."""
  if category and category not in REPLAY_AUDIT_CATEGORIES:
    allowed = ", ".join(REPLAY_AUDIT_CATEGORIES)
    raise ValueError(f"Unknown replay audit category {category!r}; expected one of: {allowed}")
  return category


def primary_mode(entry: dict[str, Any] | None) -> str:
  if not entry:
    return ""
  modes = entry.get("modes_ordered") or []
  return str(modes[0]) if modes else ""


def save_annotator_labels(
  path: Path,
  annotator_id: str,
  labels: dict[str, dict[str, Any]],
  *,
  packet_id: str = "",
) -> dict[str, Any]:
  """Replace one annotator's label map; other annotators are preserved."""
  validate_annotator_id(annotator_id)
  with annotations_lock(path):
    data = load_annotations(path, packet_id=packet_id, packet_dir=path.parent)
    merged: dict[str, dict[str, Any]] = {}
    for episode_key, entry in labels.items():
      if not isinstance(entry, dict):
        continue
      item = dict(entry)
      item["updated_at"] = item.get("updated_at") or _utc_now()
      merged[str(episode_key)] = item
    data["annotators"][annotator_id]["labels"] = merged
    save_annotations(path, data)
  return data


def save_single_episode(
  path: Path,
  annotator_id: str,
  episode_key: str,
  entry: dict[str, Any],
  *,
  packet_id: str = "",
) -> dict[str, Any]:
  """Merge one episode label for an annotator without touching others."""
  validate_annotator_id(annotator_id)
  with annotations_lock(path):
    data = load_annotations(path, packet_id=packet_id, packet_dir=path.parent)
    item = dict(entry)
    item["updated_at"] = item.get("updated_at") or _utc_now()
    data["annotators"][annotator_id]["labels"][str(episode_key)] = item
    save_annotations(path, data)
  return data


def save_replay_audit(
  path: Path,
  annotator_id: str,
  task_id: str,
  entry: dict[str, Any],
  *,
  packet_id: str = "",
) -> dict[str, Any]:
  """Merge one replay-audit note for an annotator without touching others.

  Audit notes are keyed by gold ``task_id`` (one guided replay per task), not by
  the model episode key used for taxonomy labels.
  """
  validate_annotator_id(annotator_id)
  item = dict(entry)
  item["category"] = validate_replay_category(str(item.get("category") or ""))
  item["note"] = str(item.get("note") or "")
  with annotations_lock(path):
    data = load_annotations(path, packet_id=packet_id, packet_dir=path.parent)
    if not item["category"] and not item["note"]:
      data["annotators"][annotator_id]["replay_audit"].pop(str(task_id), None)
    else:
      item["updated_at"] = item.get("updated_at") or _utc_now()
      data["annotators"][annotator_id]["replay_audit"][str(task_id)] = item
    save_annotations(path, data)
  return data


def _merge_newest(base: dict[str, Any], other: dict[str, Any]) -> dict[str, dict[str, Any]]:
  """Per key keep the entry with the newer ``updated_at`` (missing loses)."""
  merged: dict[str, dict[str, Any]] = {}
  for source in (base, other):
    for key, entry in source.items():
      if not isinstance(entry, dict):
        continue
      current = merged.get(key)
      if current is None or str(entry.get("updated_at") or "") >= str(
        current.get("updated_at") or ""
      ):
        merged[key] = dict(entry)
  return merged


def merge_annotations(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
  """Merge two annotation payloads; per (annotator, key) the entry with the
  newer ``updated_at`` wins (entries without a timestamp always lose to entries
  that have one). Covers both taxonomy labels and replay-audit notes. Used by
  the git snapshot sync."""
  out = empty_annotations(str(base.get("packet_id") or other.get("packet_id") or ""))
  for annotator_id in REGISTERED_ANNOTATORS:
    out["annotators"][annotator_id]["labels"] = _merge_newest(
      get_annotator_labels(base, annotator_id), get_annotator_labels(other, annotator_id)
    )
    out["annotators"][annotator_id]["replay_audit"] = _merge_newest(
      get_replay_audit(base, annotator_id), get_replay_audit(other, annotator_id)
    )
  return out


def annotations_summary(data: dict[str, Any]) -> dict[str, dict[str, str]]:
  """Per-episode primary mode for each annotator (for index UI)."""
  summary: dict[str, dict[str, str]] = {aid: {} for aid in REGISTERED_ANNOTATORS}
  for annotator_id in REGISTERED_ANNOTATORS:
    for episode_key, entry in get_annotator_labels(data, annotator_id).items():
      mode = primary_mode(entry)
      if mode:
        summary[annotator_id][episode_key] = mode
  return summary


def replay_audit_summary(data: dict[str, Any]) -> dict[str, dict[str, str]]:
  """Per-task replay-audit category for each annotator (for index UI)."""
  summary: dict[str, dict[str, str]] = {aid: {} for aid in REGISTERED_ANNOTATORS}
  for annotator_id in REGISTERED_ANNOTATORS:
    for task_id, entry in get_replay_audit(data, annotator_id).items():
      if not isinstance(entry, dict):
        continue
      # A bare note with no category still marks the task as audited.
      summary[annotator_id][task_id] = str(entry.get("category") or "noted")
  return summary


def load_annotator_labels_from_file(
  path: Path | None,
  annotator_id: str,
  *,
  packet_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
  packet_id = packet_dir.name if packet_dir else ""
  data = load_annotations(path, packet_id=packet_id, packet_dir=packet_dir)
  return get_annotator_labels(data, annotator_id)
