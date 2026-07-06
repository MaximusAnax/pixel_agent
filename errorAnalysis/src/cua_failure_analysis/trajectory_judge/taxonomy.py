"""CUA failure-mode taxonomy.

Encodes the 14 failure modes from `Taxonomy of CUA Failure Modes.md`, split into
two top-level categories (Perception/Grounding vs Cognitive/Planning), plus an
explicit ``other`` escape hatch so the judge is never forced to mislabel a
trajectory that genuinely does not fit (e.g. environment/harness errors, or an
apparent reward mismatch).

These enums are consumed by `schema.py` (Pydantic output schema for guided JSON
decoding) and `judge_prompt.py` (renders the taxonomy block into the system
prompt).
"""

from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    perception_grounding = "perception_grounding"
    cognitive_planning = "cognitive_planning"
    other = "other"


class FailureMode(str, Enum):
    # --- Perception / Grounding ---
    click_region_error = "click_region_error"
    visual_confusion = "visual_confusion"
    text_matching_bias = "text_matching_bias"
    resolution_scale_brittleness = "resolution_scale_brittleness"
    fine_grained_manipulation_failure = "fine_grained_manipulation_failure"
    icon_recognition_failure = "icon_recognition_failure"
    # --- Cognitive / Planning ---
    action_looping = "action_looping"
    location_hallucination = "location_hallucination"
    spatial_reasoning_error = "spatial_reasoning_error"
    goal_hallucination = "goal_hallucination"
    reasoning_drift = "reasoning_drift"
    long_horizon_memory_failure = "long_horizon_memory_failure"
    instruction_ambiguity_failure = "instruction_ambiguity_failure"
    refusal_infeasibility_error = "refusal_infeasibility_error"
    # --- Escape hatch ---
    other = "other"


# Which top-level category each failure mode belongs to.
MODE_CATEGORY: dict[FailureMode, Category] = {
    FailureMode.click_region_error: Category.perception_grounding,
    FailureMode.visual_confusion: Category.perception_grounding,
    FailureMode.text_matching_bias: Category.perception_grounding,
    FailureMode.resolution_scale_brittleness: Category.perception_grounding,
    FailureMode.fine_grained_manipulation_failure: Category.perception_grounding,
    FailureMode.icon_recognition_failure: Category.perception_grounding,
    FailureMode.action_looping: Category.cognitive_planning,
    FailureMode.location_hallucination: Category.cognitive_planning,
    FailureMode.spatial_reasoning_error: Category.cognitive_planning,
    FailureMode.goal_hallucination: Category.cognitive_planning,
    FailureMode.reasoning_drift: Category.cognitive_planning,
    FailureMode.long_horizon_memory_failure: Category.cognitive_planning,
    FailureMode.instruction_ambiguity_failure: Category.cognitive_planning,
    FailureMode.refusal_infeasibility_error: Category.cognitive_planning,
    FailureMode.other: Category.other,
}

# One-line definitions, lifted from `Taxonomy of CUA Failure Modes.md`.
MODE_DEFINITION: dict[FailureMode, str] = {
    FailureMode.click_region_error: (
        "The agent conceptually identifies the correct UI element but predicts "
        "imprecise or wrong-physical-area coordinates (output falls outside the "
        "element's actual boundary)."
    ),
    FailureMode.visual_confusion: (
        "The agent relies on superficial visual cues (shape, color, position) "
        "rather than functional semantics, mistaking one type of element for "
        "another (e.g. a light button for a search box)."
    ),
    FailureMode.text_matching_bias: (
        "The agent clicks visible text that matches a word in the instruction "
        "without verifying it is the interactive target (e.g. clicks the 'First "
        "Name' label instead of the input field beneath it)."
    ),
    FailureMode.resolution_scale_brittleness: (
        "Failure to adapt to browser zoom / screen-resolution changes; the model "
        "appears to have memorized absolute pixel positions (clicks empty space "
        "where an element used to be at a different scale)."
    ),
    FailureMode.fine_grained_manipulation_failure: (
        "Breakdown in precision when tasks require character-level cursor "
        "placement or adjusting compact components like sliders / tiny pixel "
        "regions."
    ),
    FailureMode.icon_recognition_failure: (
        "Inability to associate visual symbols with their functional purpose "
        "without explicit text labels (e.g. magnifying glass = Search, gear = "
        "Settings)."
    ),
    FailureMode.action_looping: (
        "The agent repeats the same unsuccessful action multiple times without "
        "adapting to environmental feedback (e.g. retyping a query but never "
        "clicking Search)."
    ),
    FailureMode.location_hallucination: (
        "The agent's reasoning correctly identifies the target, but it outputs "
        "fabricated / random coordinates unrelated to that target."
    ),
    FailureMode.spatial_reasoning_error: (
        "The agent incorrectly interprets relative spatial relationships such as "
        "above, below, left, or right (identifies the right landmark but the "
        "wrong side)."
    ),
    FailureMode.goal_hallucination: (
        "The agent invents user intent or sub-goals that were never specified in "
        "the original instruction and acts on that unstated assumption."
    ),
    FailureMode.reasoning_drift: (
        "Explicit chain-of-thought misleads the final action prediction rather "
        "than helping it (a self-generated thought steers it to the wrong "
        "element)."
    ),
    FailureMode.long_horizon_memory_failure: (
        "The agent loses track of key information or intermediate sub-goals after "
        "many interaction steps (drifts from the plan, forgets which items were "
        "already processed)."
    ),
    FailureMode.instruction_ambiguity_failure: (
        "Failure to resolve an underspecified query, leading to a speculative "
        "action that does not match user/evaluator expectations (e.g. changes a "
        "per-document setting when a global one was expected)."
    ),
    FailureMode.refusal_infeasibility_error: (
        "Failure to recognize that a task is impossible given the current UI "
        "state, resulting in speculative clicks on unrelated elements instead of "
        "refusing / reporting infeasibility."
    ),
    FailureMode.other: (
        "Does not fit any taxonomy mode, or the failure is due to the environment "
        "/ harness (crash, timeout, reward mismatch) rather than agent behavior. "
        "Explain in the evidence field."
    ),
}


def render_taxonomy() -> str:
    """Render the taxonomy as a numbered text block for the judge's system prompt."""
    lines: list[str] = []
    headers = {
        Category.perception_grounding: "PERCEPTION / GROUNDING ERRORS",
        Category.cognitive_planning: "COGNITIVE / PLANNING ERRORS",
        Category.other: "ESCAPE HATCH",
    }
    for cat in (Category.perception_grounding, Category.cognitive_planning, Category.other):
        lines.append(f"\n## {headers[cat]} (category = \"{cat.value}\")")
        for mode in FailureMode:
            if MODE_CATEGORY[mode] is cat:
                lines.append(f'- "{mode.value}": {MODE_DEFINITION[mode]}')
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_taxonomy())
    print(f"\n{len(FailureMode)} modes total ({len(FailureMode) - 1} canonical + other)")
