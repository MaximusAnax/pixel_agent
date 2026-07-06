"""Pydantic output schema for the VLM judge.

`Classification.model_json_schema()` is fed to vLLM's guided-JSON decoding so the
7B judge is forced to emit valid, enum-constrained JSON. Field order matters: the
schema is generated top-to-bottom, so `analysis` comes first to let the model
"think" (cite the failing step, reason about cause) before committing to a label.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cua_failure_analysis.trajectory_judge.taxonomy import Category, FailureMode


class Classification(BaseModel):
    analysis: str = Field(
        description=(
            "Step-by-step reasoning: what the task wanted, what the agent did, "
            "and where/why the trajectory first went wrong. Cite specific step "
            "numbers and screenshots. END this field with a sentence of the exact "
            "form: 'Therefore the category is <category> and the specific mode is "
            "<mode>.' using the exact taxonomy names."
        )
    )
    category: Category = Field(
        description=(
            "Commit to the top-level branch FIRST: perception_grounding (the agent "
            "knew what it wanted but failed visually/physically), cognitive_planning "
            "(its reasoning/intent/memory/strategy was wrong), or other."
        )
    )
    primary_failure_mode: FailureMode = Field(
        description=(
            "The single dominant mode, which MUST belong to the category you just "
            "chose and MUST match the mode named at the end of your analysis. Do "
            "NOT default to click_region_error."
        )
    )
    failing_step: int = Field(
        description=(
            "Index (step_num) of the step where the trajectory FIRST clearly went "
            "wrong. Use -1 if it cannot be localized to a single step."
        )
    )
    secondary_failure_modes: list[FailureMode] = Field(
        default_factory=list,
        description="Up to 3 additional contributing modes, if any (else empty).",
    )
    confidence: float = Field(
        description="Confidence in the primary label, a number from 0.0 to 1.0."
    )


if __name__ == "__main__":
    import json

    print(json.dumps(Classification.model_json_schema(), indent=2))
