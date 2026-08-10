"""Judge prompt templates and taxonomy anchors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cua_failure_analysis.taxonomy import ALL_LEAVES

DECISION_ORDER = """
Disambiguation order at t* (for choosing between confusable leaves and finding
the most central mode — it does NOT limit how many modes you list):
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

Identify EVERY failure mode that applies at step t*, from this taxonomy
(all-applicable policy — list each mode the evidence at t* supports, ordered
most-central/root-cause first):
{LEAF_LIST}

{DECISION_ORDER}

Rules:
- Eval context (OSWorld evaluator bundle) is ground truth for **what OSWorld checks**.
  The failure-mode label is about **agent behavior at t***.
- If the agent appears to meet eval criteria on available evidence but OSWorld marked
  fail, suggest `evaluator_mismatch` in `meta_labels`.
- Human reference (text + observation images) is **NON-BINDING** — a viable path, not
  the only valid path. Do **not** overfit: if the agent's actions diverge from the human
  sequence but still progress toward OSWorld success criteria, that can be correct.
  Prefer labeling agent failure modes over "didn't match human."
  Do not require step-wise alignment between human and agent traces (lengths/order often differ).
- **Grounding comparison:** OpenCUA logs two representations per step —
  **model code (CoT)** uses normalized coords (0–1); **executed action (trajectory)**
  uses absolute pixels. They usually describe the same intent after conversion.
  When they **diverge beyond coordinate rounding**, treat as grounding evidence:
  prefer Click Region Error, Location Hallucination, or Fine-Grained Manipulation Failure
  depending on screenshot + stated intent. When model code targets element A in CoT but
  executed click lands on B, cite both in `evidence_cot_span`.
- Use screenshot + CoT evidence; do not assume reference trajectories are the only valid path.
- List every mode that applies at t* in `modes_ordered`, most-central-first. Do not
  pad: include a mode only when the evidence at t* supports it. One mode is a valid
  answer when only one applies.
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
  *,
  canonical_instruction: str = "",
  eval_bundle: str = "",
  executed_action: str = "",
  model_code: str = "",
  stated_intent: str = "",
  grounding_mismatch: bool | None = None,
  human_reference_text: str = "",
) -> str:
  """Build the judge user prompt.

  Prefer structured action fields when provided; fall back to ``action_json``.
  """
  canon = (canonical_instruction or instruction or "").strip()
  bundle = (eval_bundle or eval_message or "").strip() or "(none)"
  human_block = (human_reference_text or "").strip() or "(none — text-only or oracle not ready)"

  if executed_action or model_code or stated_intent:
    mismatch_str = (
      "unknown" if grounding_mismatch is None else str(bool(grounding_mismatch))
    )
    action_block = f"""Executed action (trajectory — what ran on VM):
{executed_action or "(none)"}

Model code (CoT — what model proposed):
{model_code or "(none)"}

Stated intent (CoT Action section):
{stated_intent or "(none)"}

Grounding pre-check: {mismatch_str} (programmatic: proposed vs executed coords)
Coordinate note: model uses normalized 0-1; trajectory uses pixels (1920x1080 assumed unless known)"""
  else:
    action_block = f"""Action at t*:
{action_json}"""

  return f"""Canonical task instruction:
{canon}

OSWorld evaluator bundle:
{bundle}

Human reference path (NON-BINDING — one viable solution, not required):
{human_block}
Note: agent path length/order may differ; do not require step-wise alignment.
Human observation images (if any) are attached separately before the model observation.

{action_block}

Chain-of-thought (reasoning) at t*:
{cot}

Previous steps (compressed):
{previous_summary}

Respond with ONLY the following JSON object and nothing else. Do not write any
reasoning, preamble, or explanation outside the JSON. Put your evidence inside
`evidence_cot_span`. `modes_ordered` MUST contain one or more of the exact leaf
names above, ordered most-central-first (the root-cause mode first).
{{
  "modes_ordered": ["<exact leaf name>", "<additional applicable leaf names>"],
  "propagated": false,
  "meta_labels": [],
  "evidence_cot_span": "<quote or brief evidence>",
  "confidence": 0.0
}}
"""


def format_human_reference_text(human_reference_steps: list[dict[str, Any]] | None) -> str:
  """Render human steps as text for the prompt (images attached separately)."""
  if not human_reference_steps:
    return ""
  lines: list[str] = []
  for i, row in enumerate(human_reference_steps, start=1):
    action = str(row.get("action_text") or row.get("action") or "").strip()
    has_img = bool(row.get("image_path"))
    img_note = " [image attached]" if has_img else ""
    lines.append(f"  h={i}: {action}{img_note}")
  return "\n".join(lines)
