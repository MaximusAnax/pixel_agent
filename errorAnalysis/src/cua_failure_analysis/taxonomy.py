"""16-leaf failure taxonomy constants."""

from enum import Enum


class FailureLeaf(str, Enum):
  CLICK_REGION_ERROR = "Click Region Error"
  VISUAL_CONFUSION = "Visual Confusion (Primitive Reliance)"
  TEXT_MATCHING_BIAS = "Text Matching Bias"
  RESOLUTION_SCALE_BRITTLENESS = "Resolution/Scale Brittleness"
  FINE_GRAINED_MANIPULATION = "Fine-Grained Manipulation Failure"
  SOFTWARE_COMMONSENSE = "Software Commonsense (Icon Recognition) Failure"
  ACTION_LOOPING = "Action Looping (Repetition)"
  LOCATION_HALLUCINATION = "Location Hallucination"
  SPATIAL_REASONING = "Spatial Reasoning Error"
  GOAL_HALLUCINATION = "Goal Hallucination"
  REASONING_DRIFT = "Reasoning Drift"
  LONG_HORIZON_MEMORY = "Long-Horizon Memory Failure"
  INSTRUCTION_AMBIGUITY = "Instruction Ambiguity Failure"
  REFUSAL_INFEASIBILITY = "Refusal/Infeasibility Error"
  HIDDEN_OPERATION_BLINDNESS = "Hidden Operation Blindness"
  CROSS_APP_CONTEXT_LOSS = "Cross-Application Context Loss"


PERCEPTION_LEAVES = {
  FailureLeaf.CLICK_REGION_ERROR,
  FailureLeaf.VISUAL_CONFUSION,
  FailureLeaf.TEXT_MATCHING_BIAS,
  FailureLeaf.RESOLUTION_SCALE_BRITTLENESS,
  FailureLeaf.FINE_GRAINED_MANIPULATION,
  FailureLeaf.SOFTWARE_COMMONSENSE,
}

COGNITIVE_LEAVES = {
  FailureLeaf.ACTION_LOOPING,
  FailureLeaf.LOCATION_HALLUCINATION,
  FailureLeaf.SPATIAL_REASONING,
  FailureLeaf.GOAL_HALLUCINATION,
  FailureLeaf.REASONING_DRIFT,
  FailureLeaf.LONG_HORIZON_MEMORY,
  FailureLeaf.INSTRUCTION_AMBIGUITY,
  FailureLeaf.REFUSAL_INFEASIBILITY,
  FailureLeaf.HIDDEN_OPERATION_BLINDNESS,
  FailureLeaf.CROSS_APP_CONTEXT_LOSS,
}

ALL_LEAVES = PERCEPTION_LEAVES | COGNITIVE_LEAVES

TASK_TAG_GATED = {
  FailureLeaf.RESOLUTION_SCALE_BRITTLENESS: "zoom_stress",
  FailureLeaf.INSTRUCTION_AMBIGUITY: "underspecified",
  FailureLeaf.REFUSAL_INFEASIBILITY: "infeasible",
  FailureLeaf.FINE_GRAINED_MANIPULATION: "fine_manipulation",
  FailureLeaf.CROSS_APP_CONTEXT_LOSS: "cross_app",
  FailureLeaf.SPATIAL_REASONING: "relational",
}
