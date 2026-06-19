"""Judge prompt templates and taxonomy anchors."""

from __future__ import annotations

from pathlib import Path

import yaml

from cua_failure_analysis.taxonomy import ALL_LEAVES

DECISION_ORDER = """
Global decision order at t*:
1. Action Looping if same action repeated >=3 times without state change
2. Spatial Reasoning Error if relational instruction + landmark in CoT + wrong relative click
3. Click Region Error if CoT names T and click near but outside T bbox
4. Location Hallucination if CoT names T and click far from T
5. Hidden Operation Blindness if goal understood but hidden affordance never attempted
6. Otherwise apply leaf-specific rules
"""

LEAF_LIST = "\n".join(f"- {leaf.value}" for leaf in sorted(ALL_LEAVES, key=lambda x: x.value))


def build_system_prompt(anchors_yaml: Path | None = None) -> str:
  anchor_block = ""
  if anchors_yaml and anchors_yaml.exists():
    data = yaml.safe_load(anchors_yaml.read_text())
    lines = ["## Calibration anchors"]
    for leaf, examples in (data or {}).items():
      lines.append(f"\n### {leaf}")
      for ex in examples[:5]:
        lines.append(f"- {ex}")
    anchor_block = "\n".join(lines)

  return f"""You are an expert annotator for computer-use agent failure modes.

Classify the failure at step t* using EXACTLY ONE primary label from this taxonomy:
{LEAF_LIST}

{DECISION_ORDER}

Rules:
- Use screenshot + CoT evidence only; do not assume reference trajectories are the only valid path.
- Assign secondary labels only if multiple modes clearly co-occur at the same step.
- Set propagated=true only if this step is downstream of an earlier root error.
- Output valid JSON only.

{anchor_block}
"""


def build_user_prompt(
  instruction: str,
  cot: str,
  action_json: str,
  eval_message: str,
  previous_summary: str,
) -> str:
  return f"""Task instruction:
{instruction}

Chain-of-thought at t*:
{cot}

Action at t*:
{action_json}

Evaluator message:
{eval_message}

Previous steps (compressed):
{previous_summary}

Return JSON:
{{
  "primary_mode": "<exact leaf name>",
  "secondary_modes": [],
  "propagated": false,
  "meta_labels": [],
  "evidence_cot_span": "<quote or brief evidence>",
  "confidence": 0.0
}}
"""
