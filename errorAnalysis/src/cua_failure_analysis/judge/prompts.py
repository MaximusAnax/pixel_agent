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


# --- Protocol v2 (meeting 2026-08-07, Decision 5): multi-label, both ---
# --- trajectories, OSWorld score + evaluator output in context.       ---


def build_system_prompt_v2(
  anchors_yaml: Path | None = None,
  decision_order: str | None = None,
  extra_rules: list[str] | None = None,
) -> str:
  """Multi-label system prompt: select ALL applicable failure modes.

  ``decision_order`` overrides the default tie-break text (used by the
  autoResearch loop to explore orderings); ``extra_rules`` appends rule lines.
  """
  anchor_block = ""
  if anchors_yaml and anchors_yaml.exists():
    data = yaml.safe_load(anchors_yaml.read_text())
    lines = ["## Calibration anchors"]
    for leaf, examples in (data or {}).items():
      lines.append(f"\n### {leaf}")
      for ex in examples[:5]:
        lines.append(f"- {ex}")
    anchor_block = "\n".join(lines)

  order = decision_order if decision_order is not None else DECISION_ORDER
  rules = [
    "Select ALL failure modes that are genuinely present, not just the primary.",
    "List modes most-responsible-first; the first entry is the primary mode.",
    "Use screenshot + CoT evidence; the reference trajectory shows ONE valid "
    "path, not the only valid path — do not mark deviation itself as failure.",
    "Set propagated=true only for modes downstream of an earlier root error.",
    "Output valid JSON only.",
  ]
  rules.extend(extra_rules or [])
  rule_block = "\n".join(f"- {r}" for r in rules)

  return f"""You are an expert annotator for computer-use agent failure modes.

Identify the failure modes at step t* using labels from this taxonomy:
{LEAF_LIST}

{order}

Rules:
{rule_block}

{anchor_block}
"""


def build_user_prompt_v2(
  instruction: str,
  cot: str,
  action_json: str,
  previous_summary: str,
  reference_summary: str | None = None,
  osworld_score: float | None = None,
  eval_output: str | None = None,
) -> str:
  """User prompt for protocol v2.

  ``reference_summary`` is the compressed human/reference trajectory;
  ``osworld_score`` and ``eval_output`` are the OSWorld metric result and the
  evaluator test output. Each section is included only when provided so the
  autoResearch loop can ablate context pieces independently.
  """
  sections = [
    f"Task instruction:\n{instruction}",
    f"Chain-of-thought at t*:\n{cot}",
    f"Action at t*:\n{action_json}",
    f"Agent trajectory so far (compressed):\n{previous_summary or '(none)'}",
  ]
  if reference_summary is not None:
    sections.append(f"Reference (human) trajectory (compressed):\n{reference_summary}")
  if osworld_score is not None:
    sections.append(f"OSWorld metric score:\n{osworld_score}")
  if eval_output is not None:
    sections.append(f"Evaluator test output:\n{eval_output}")

  sections.append(
    """Return JSON:
{
  "modes": ["<leaf name>", "..."],
  "propagated": false,
  "meta_labels": [],
  "evidence_cot_span": "<quote or brief evidence>",
  "confidence": 0.0
}"""
  )
  return "\n\n".join(sections)
