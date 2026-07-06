"""Tests for mattlab shared Babel layout defaults."""

from __future__ import annotations

from pathlib import Path

from cua_failure_analysis.babel_layout import default_mattlab_layout, layout_from_env

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ENV = ROOT / "config" / "babel.env.example"


def test_default_mattlab_layout_paths():
  layout = default_mattlab_layout()
  assert layout.group_root == "/data/group_data/mattlab/pixel_agent"
  assert layout.shared_repo.endswith("/pixelAgent")
  assert layout.error_analysis.endswith("/pixelAgent/errorAnalysis")
  assert layout.shared_output_root.endswith("/outputs")
  assert layout.packet_staging.endswith("/review_packets")


def test_layout_from_env_overrides():
  layout = layout_from_env(
    {
      "BABEL_GROUP_ROOT": "/data/group_data/mattlab/pixel_agent",
      "BABEL_SHARED_REPO": "/data/group_data/mattlab/pixel_agent/pixelAgent",
    }
  )
  assert layout.error_analysis == "/data/group_data/mattlab/pixel_agent/pixelAgent/errorAnalysis"


def test_babel_env_example_declares_shared_vars():
  text = EXAMPLE_ENV.read_text(encoding="utf-8")
  for var in (
    "BABEL_SHARED_REPO",
    "BABEL_SHARED_OUTPUT_ROOT",
    "BABEL_SHARED_VENV",
    "BABEL_SHARED_ERROR_ANALYSIS",
  ):
    assert var in text, f"missing {var} in babel.env.example"
