"""Tests for vendored OSWorld metadata loaders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cua_failure_analysis.osworld.eval_bundle import format_eval_bundle, getter_name_for_result_type
from cua_failure_analysis.osworld.human_ref import load_human_reference
from cua_failure_analysis.osworld.metadata import load_sources, resolve_pin_dir, task_lookup

EXAMPLE_TASK = "06fe7178-4491-4589-810f-2e2bc9502122"


@pytest.fixture(scope="module")
def pin_dir() -> Path:
  sources = load_sources()
  root = resolve_pin_dir(sources)
  if not (root / "tasks").exists():
    pytest.skip(f"Vendored OSWorld cache missing at {root}; run vendor_osworld_metadata.py")
  return root


def test_sources_pin_matches_cache(pin_dir: Path):
  sources = load_sources()
  assert pin_dir.name == sources.pin
  manifest = json.loads((pin_dir / "manifest.json").read_text(encoding="utf-8"))
  assert manifest["pin"] == sources.pin
  assert manifest["task_count"] >= 1


def test_task_lookup_example(pin_dir: Path):
  task = task_lookup(EXAMPLE_TASK, domain="chrome", pin_dir=pin_dir)
  assert task["id"] == EXAMPLE_TASK
  assert "bring back the last tab" in task["instruction"].lower()
  assert task["evaluator"]["func"] == "is_expected_tabs"
  assert task["_domain"] == "chrome"


def test_human_reference_example(pin_dir: Path):
  ref = load_human_reference(EXAMPLE_TASK, domain="chrome", pin_dir=pin_dir)
  assert ref.single_action
  assert any("HOTKEY" in a for a in ref.single_action)
  assert ref.grouped_action


def test_getter_alias():
  assert getter_name_for_result_type("open_tabs_info") == "get_open_tabs_info"


def test_format_eval_bundle_example(pin_dir: Path):
  task = task_lookup(EXAMPLE_TASK, domain="chrome", pin_dir=pin_dir)
  bundle = format_eval_bundle(task, result_txt=0.0, pin_dir=pin_dir)
  assert "OSWorld outcome: fail" in bundle
  assert "Canonical instruction:" in bundle
  assert "is_expected_tabs" in bundle
  assert "get_open_tabs_info" in bundle
  assert "lonelyplanet" in bundle.lower() or "tripadvisor" in bundle.lower()
