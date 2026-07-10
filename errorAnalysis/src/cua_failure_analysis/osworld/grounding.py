"""Compare OpenCUA CoT model code (normalized) vs executed trajectory (pixels)."""

from __future__ import annotations

import math
import re
from typing import Any

CLICK_OR_MOVE_RE = re.compile(
  r"pyautogui\.(?:click|moveTo)\s*\(\s*(?:x\s*=\s*)?([0-9.]+)\s*,\s*(?:y\s*=\s*)?([0-9.]+)",
  re.I,
)
DRAG_RE = re.compile(
  r"pyautogui\.dragTo\s*\(\s*(?:x\s*=\s*)?([0-9.]+)\s*,\s*(?:y\s*=\s*)?([0-9.]+)",
  re.I,
)


def _first_xy(code: str | None) -> tuple[float, float] | None:
  if not code:
    return None
  for pattern in (CLICK_OR_MOVE_RE, DRAG_RE):
    match = pattern.search(code)
    if match:
      return float(match.group(1)), float(match.group(2))
  return None


def _looks_normalized(x: float, y: float) -> bool:
  return 0.0 <= x <= 1.5 and 0.0 <= y <= 1.5 and (x <= 1.0 or y <= 1.0)


def compare_proposed_vs_executed(
  model_code: str | None,
  raw_code: str | None,
  *,
  screen_width: int = 1920,
  screen_height: int = 1080,
  tolerance: float = 0.05,
) -> dict[str, Any]:
  """Return coord comparison + grounding_mismatch flag.

  Model CoT typically uses normalized 0–1 coords; trajectory uses absolute pixels.
  """
  model_xy = _first_xy(model_code)
  exec_xy = _first_xy(raw_code)

  coords_model_normalized: list[float] | None = None
  coords_model_pixels_est: list[float] | None = None
  coords_executed: list[float] | None = None

  if model_xy is not None:
    mx, my = model_xy
    if _looks_normalized(mx, my):
      coords_model_normalized = [mx, my]
      coords_model_pixels_est = [mx * screen_width, my * screen_height]
    else:
      coords_model_pixels_est = [mx, my]
      coords_model_normalized = [mx / screen_width, my / screen_height]

  if exec_xy is not None:
    ex, ey = exec_xy
    if _looks_normalized(ex, ey):
      coords_executed = [ex * screen_width, ey * screen_height]
    else:
      coords_executed = [ex, ey]

  grounding_mismatch = False
  distance_frac: float | None = None
  if coords_executed is not None and coords_model_pixels_est is not None:
    dx = coords_executed[0] - coords_model_pixels_est[0]
    dy = coords_executed[1] - coords_model_pixels_est[1]
    dist = math.hypot(dx, dy)
    diagonal = math.hypot(screen_width, screen_height) or 1.0
    distance_frac = dist / diagonal
    grounding_mismatch = distance_frac > tolerance

  return {
    "coords_executed": coords_executed,
    "coords_model_normalized": coords_model_normalized,
    "coords_model_pixels_est": coords_model_pixels_est,
    "grounding_mismatch": grounding_mismatch,
    "distance_frac": distance_frac,
    "tolerance": tolerance,
    "screen_width": screen_width,
    "screen_height": screen_height,
  }
