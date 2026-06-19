"""Prevalence and confidence intervals."""

from __future__ import annotations

import math
from collections import Counter

from cua_failure_analysis.taxonomy import ALL_LEAVES


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
  if n == 0:
    return (0.0, 0.0)
  p = successes / n
  denom = 1 + z**2 / n
  center = (p + z**2 / (2 * n)) / denom
  margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
  return (max(0.0, center - margin), min(1.0, center + margin))


def prevalence_table(
  attributions: list[dict],
  model_id: str | None = None,
) -> list[dict]:
  rows = attributions
  if model_id:
    rows = [r for r in rows if r.get("model_id") == model_id]
  n = len(rows)
  counts = Counter(r.get("primary_mode", "Unresolved") for r in rows)
  table = []
  for leaf in sorted(ALL_LEAVES, key=lambda x: x.value):
    c = counts.get(leaf.value, 0)
    lo, hi = wilson_ci(c, n)
    table.append(
      {
        "leaf": leaf.value,
        "count": c,
        "n_failures": n,
        "prevalence": c / n if n else 0.0,
        "ci_low": lo,
        "ci_high": hi,
      }
    )
  return table
