"""Multi-annotator review labels (schema v2) with v1 migration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTERED_ANNOTATORS: tuple[str, ...] = ("abdoul", "raghav")
ANNOTATIONS_FILENAME = "annotations.json"
LEGACY_LABELS_FILENAME = "human_labels.json"
SCHEMA_VERSION = 2


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_annotations(packet_id: str) -> dict[str, Any]:
  return {
    "schema_version": SCHEMA_VERSION,
    "packet_id": packet_id,
    "annotators": {annotator_id: {"labels": {}} for annotator_id in REGISTERED_ANNOTATORS},
  }


def validate_annotator_id(annotator_id: str) -> str:
  if annotator_id not in REGISTERED_ANNOTATORS:
    allowed = ", ".join(REGISTERED_ANNOTATORS)
    raise ValueError(f"Unknown annotator {annotator_id!r}; expected one of: {allowed}")
  return annotator_id


def migrate_v1_to_v2(data: dict[str, Any], packet_id: str) -> dict[str, Any]:
  """Convert legacy human_labels.json (v1) into v2 annotations."""
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
  if version != SCHEMA_VERSION:
    raise ValueError(f"Unsupported annotations schema_version: {version!r}")

  out = empty_annotations(packet_id)
  out["packet_id"] = str(data.get("packet_id") or packet_id)
  annotators = data.get("annotators")
  if not isinstance(annotators, dict):
    return out

  for annotator_id in REGISTERED_ANNOTATORS:
    block = annotators.get(annotator_id) or {}
    labels = block.get("labels") if isinstance(block, dict) else {}
    if isinstance(labels, dict):
      out["annotators"][annotator_id]["labels"] = dict(labels)
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


def save_annotations(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
  data = load_annotations(path, packet_id=packet_id, packet_dir=path.parent)
  item = dict(entry)
  item["updated_at"] = item.get("updated_at") or _utc_now()
  data["annotators"][annotator_id]["labels"][str(episode_key)] = item
  save_annotations(path, data)
  return data


def annotations_summary(data: dict[str, Any]) -> dict[str, dict[str, str]]:
  """Per-episode primary mode for each annotator (for index UI)."""
  summary: dict[str, dict[str, str]] = {aid: {} for aid in REGISTERED_ANNOTATORS}
  for annotator_id in REGISTERED_ANNOTATORS:
    for episode_key, entry in get_annotator_labels(data, annotator_id).items():
      mode = primary_mode(entry)
      if mode:
        summary[annotator_id][episode_key] = mode
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
