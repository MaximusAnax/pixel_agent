"""Load vendored OSWorld task JSONs and source pin config."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
DEFAULT_SOURCES = CONFIG_DIR / "osworld_sources.yaml"
OSWORLD_CACHE_ROOT = CONFIG_DIR / "osworld"


@dataclass(frozen=True)
class OsworldSources:
  pin: str
  osworld_repo: str
  osworld_commit: str
  osworld_task_template: str
  metrics_dir: str
  getters_init: str
  human_repo: str
  human_commit: str
  human_task_template: str
  screen_width: int
  screen_height: int
  grounding_mismatch_tolerance: float
  sources_path: Path

  @property
  def pin_dir(self) -> Path:
    return OSWORLD_CACHE_ROOT / self.pin


def load_sources(path: Path | None = None) -> OsworldSources:
  sources_path = path or DEFAULT_SOURCES
  raw = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
  osw = raw["osworld"]
  human = raw["osworld_human"]
  screen = raw.get("default_screen") or {}
  return OsworldSources(
    pin=str(raw["pin"]),
    osworld_repo=str(osw["repo"]),
    osworld_commit=str(osw["commit"]),
    osworld_task_template=str(osw["task_path_template"]),
    metrics_dir=str(osw["metrics_dir"]),
    getters_init=str(osw["getters_init"]),
    human_repo=str(human["repo"]),
    human_commit=str(human["commit"]),
    human_task_template=str(human["task_path_template"]),
    screen_width=int(screen.get("width", 1920)),
    screen_height=int(screen.get("height", 1080)),
    grounding_mismatch_tolerance=float(raw.get("grounding_mismatch_tolerance", 0.05)),
    sources_path=sources_path,
  )


def resolve_pin_dir(sources: OsworldSources | None = None) -> Path:
  src = sources or load_sources()
  return src.pin_dir


def _domain_index(pin_dir: Path) -> dict[str, str]:
  """Map task_id -> domain from vendored tasks/ tree or manifest."""
  index: dict[str, str] = {}
  tasks_root = pin_dir / "tasks"
  if tasks_root.exists():
    for path in tasks_root.glob("*/*.json"):
      index[path.stem] = path.parent.name
  manifest_path = pin_dir / "manifest.json"
  if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest.get("tasks", []):
      tid = row.get("task_id")
      domain = row.get("domain")
      if tid and domain:
        index[str(tid)] = str(domain)
  return index


def task_lookup(
  task_id: str,
  domain: str | None = None,
  *,
  pin_dir: Path | None = None,
  sources: OsworldSources | None = None,
) -> dict[str, Any]:
  """Load a vendored OSWorld task JSON by task_id (and optional domain)."""
  src = sources or load_sources()
  root = pin_dir or src.pin_dir
  resolved_domain = domain
  if not resolved_domain:
    resolved_domain = _domain_index(root).get(task_id)
  if not resolved_domain:
    raise FileNotFoundError(
      f"No domain for task_id={task_id!r} under {root}; vendor metadata first"
    )
  path = root / "tasks" / resolved_domain / f"{task_id}.json"
  if not path.exists():
    raise FileNotFoundError(f"Missing vendored task JSON: {path}")
  data = json.loads(path.read_text(encoding="utf-8"))
  data["_osworld_task_path"] = str(path.relative_to(CONFIG_DIR.parent))
  data["_domain"] = resolved_domain
  return data


def list_evaluator_funcs(pin_dir: Path | None = None) -> list[str]:
  """Unique evaluator.func values across vendored task JSONs."""
  root = pin_dir or resolve_pin_dir()
  funcs: set[str] = set()
  for path in (root / "tasks").glob("*/*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    evaluator = data.get("evaluator") or {}
    func = evaluator.get("func")
    if isinstance(func, str) and func:
      funcs.add(func)
    elif isinstance(func, list):
      for item in func:
        if isinstance(item, str) and item:
          funcs.add(item)
  return sorted(funcs)
