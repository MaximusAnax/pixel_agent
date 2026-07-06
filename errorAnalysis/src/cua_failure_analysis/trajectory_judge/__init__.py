"""Whole-trajectory CUA failure judge (local vLLM and/or Anthropic API).

This subpackage classifies an *entire* failed OSWorld trajectory into one failure
mode (plus analysis, category, failing step, secondaries, confidence) using a
vision-language "judge". Two interchangeable backends emit the SAME
``Classification`` schema so their labels are directly comparable:

- ``backends.local_vllm.LocalVLLMJudge`` — offline, batched vLLM (Qwen2.5-VL
  7B/32B/A3B) with guided-JSON decoding. Runs on a GPU (Babel).
- ``backends.anthropic_api.AnthropicTrajectoryJudge`` — Claude API with a forced
  tool schema for structured output. Runs anywhere with an API key.

``run_judge.py`` is the unified entry point (``--backend local|api|both``).

This is a whole-trajectory complement to the per-step ``attribution`` pipeline in
the parent package; both share the project's failure taxonomy conceptually but the
trajectory judge keeps its own snake_case enum taxonomy (``taxonomy.py``), which
its schema, viewer, and existing classification outputs are keyed to.
"""
