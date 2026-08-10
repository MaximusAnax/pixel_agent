"""The one mutable artifact: a candidate attribution policy.

A candidate is a closed parameter set (unknown keys are rejected — the loop
must never grow scope by inventing fields). It configures BOTH tiers of the
attribution pipeline:
  - detectors: Tier-1 programmatic detector thresholds/order (offline, free)
  - judge: VLM judge protocol + context ablation flags (live, costs money)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

SCHEMA_VERSION = 1

DETECTOR_NAMES = (
  "action_looping",
  "spatial_reasoning",
  "click_region_or_location",
  "text_matching_bias",
  "long_horizon",
)


@dataclass
class DetectorParams:
  min_repeat: int = 3
  near_margin_ratio: float = 1.5
  far_threshold_px: float = 80.0
  long_horizon_threshold_ratio: float = 0.7
  long_horizon_min_total_steps: int = 10
  # First matching detector wins, in this order. Removing a name disables it.
  order: list[str] = field(default_factory=lambda: list(DETECTOR_NAMES))

  def validate(self) -> None:
    if self.min_repeat < 2:
      raise ValueError("min_repeat must be >= 2")
    if not 0 < self.near_margin_ratio <= 10:
      raise ValueError("near_margin_ratio out of range (0, 10]")
    if not 0 < self.far_threshold_px <= 5000:
      raise ValueError("far_threshold_px out of range (0, 5000]")
    if not 0 < self.long_horizon_threshold_ratio <= 1:
      raise ValueError("long_horizon_threshold_ratio out of range (0, 1]")
    unknown = set(self.order) - set(DETECTOR_NAMES)
    if unknown:
      raise ValueError(f"Unknown detectors in order: {sorted(unknown)}")


@dataclass
class JudgeParams:
  protocol: str = "v1"  # "v1" | "v2_multilabel"
  model: str = "opencua-7b"
  base_url: str = "http://localhost:8000/v1"
  anchors_path: str | None = "config/judge_anchors.yaml"  # relative to errorAnalysis/
  prev_steps_k: int = 3
  include_reference_trajectory: bool = True
  include_osworld_score: bool = True
  include_eval_output: bool = True
  include_screenshot: bool = True
  decision_order: str | None = None  # None = library default text
  extra_rules: list[str] = field(default_factory=list)
  max_tokens: int = 512
  expected_output_tokens: int = 256  # for budgeting

  def validate(self) -> None:
    if self.protocol not in ("v1", "v2_multilabel"):
      raise ValueError(f"Unknown judge protocol: {self.protocol!r}")
    if not 0 <= self.prev_steps_k <= 20:
      raise ValueError("prev_steps_k out of range [0, 20]")


@dataclass
class Candidate:
  name: str
  notes: str = ""
  schema_version: int = SCHEMA_VERSION
  detectors: DetectorParams = field(default_factory=DetectorParams)
  judge: JudgeParams = field(default_factory=JudgeParams)

  def validate(self) -> None:
    if self.schema_version != SCHEMA_VERSION:
      raise ValueError(f"Unsupported candidate schema_version: {self.schema_version}")
    if not self.name:
      raise ValueError("Candidate needs a name")
    self.detectors.validate()
    self.judge.validate()

  def as_dict(self) -> dict:
    return asdict(self)

  def content_hash(self) -> str:
    payload = self.as_dict()
    payload.pop("notes", None)  # notes are commentary, not behavior
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _strict_kwargs(cls, data: dict, ctx: str) -> dict:
  allowed = set(cls.__dataclass_fields__)
  unknown = set(data) - allowed
  if unknown:
    raise ValueError(f"Unknown keys in {ctx}: {sorted(unknown)}")
  return data


def candidate_from_dict(data: dict) -> Candidate:
  data = dict(data)
  det = _strict_kwargs(DetectorParams, dict(data.pop("detectors", {}) or {}), "detectors")
  jud = _strict_kwargs(JudgeParams, dict(data.pop("judge", {}) or {}), "judge")
  top = _strict_kwargs(Candidate, data, "candidate")
  top.pop("detectors", None)
  top.pop("judge", None)
  cand = Candidate(detectors=DetectorParams(**det), judge=JudgeParams(**jud), **top)
  cand.validate()
  return cand


def load_candidate(path: Path) -> Candidate:
  return candidate_from_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def save_candidate(candidate: Candidate, path: Path) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    yaml.safe_dump(candidate.as_dict(), sort_keys=False), encoding="utf-8"
  )


def apply_overrides(base: Candidate, overrides: dict, name: str) -> Candidate:
  """Produce a new candidate = base + nested overrides (strict keys)."""
  data = base.as_dict()
  for section in ("detectors", "judge"):
    sec = overrides.get(section, {}) or {}
    if not isinstance(sec, dict):
      raise ValueError(f"{section} override must be a mapping")
    data[section].update(sec)
  for key, value in overrides.items():
    if key in ("detectors", "judge"):
      continue
    data[key] = value
  data["name"] = name
  return candidate_from_dict(data)
