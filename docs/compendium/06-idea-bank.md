# 6 — Idea bank

Everything proposed across meetings, ideation docs, and paper-idea assignments.
Kept because the project's history shows ideas resurface: Memory Inception was
"read something cool that didn't go anywhere" in June and became the documented
stretch goal by August.

**Status key:** `active` — being worked · `stretch` — approved but conditional ·
`parked` — proposed, not scheduled · `closed` — explored and dropped

---

## Directions currently on the table (from the meeting doc)

The top-level fork, stated plainly in the most recent notes:

1. **OSWorld error analysis** — the current path. Includes a possible spin-off:
   *release a proper OSWorld-Human dataset with actual trajectories.*
   - Risk noted: websites/software drift, so recorded trajectories go stale.
   - Risk noted: frontier models are evaluated on OSWorld **v2.0** — is this
     benchmark still relevant?
   - Risk noted: if frontier models don't make many errors, is failure analysis
     only relevant to small models?
2. **Better CUA (generation-based)**
3. **Better CUA (small model)**

And the natural next experiment now that the environment + grounding model exist —
how much farther do we get with: **(A)** a frontier model, **(B)** a frontier model
that sees the human trajectories, **(C)** a favorite local model?

> (B) is the important one. It is the ceiling experiment, and the UI-TARS-72B
> 60/361 result is a first, alarming datapoint on it.

---

## Perception & grounding

| Idea | Origin | Status | Notes |
|---|---|---|---|
| **Screenshot generation as a grounding method** | Abdoul | parked | Generate grounding labels with an image diffusion model (SD3). Open problem: if you draw a red circle around the click target, how do you find it again? Options: traditional CV, or generate a marker highly unusual for UIs but easy for diffusion models — **houndstooth** was the concrete suggestion. |
| **Two-model separation of perception and planning** | Raghav | parked | One model for candidate selection, one for action output; optional third for tool calls (web search, docs lookup). Rationale: separating perception from planning may be more efficient for small models with limited knowledge. |
| **Special "call-another-model" action** | Raghav | parked | Main VLM delegates bounding-box/grounding reasoning to a specialist model. |
| **Orthogonal icon-meaning data sources** | Amaad | parked | PowerPoint documentation, webpage alt-text — to attack the icon-recognition gap with data the Qwen lab likely didn't train on. |
| **Novel dataset not in Qwen training data** | Amaad | parked | Differentiation strategy; synthetic data gen, augmentation from paired screenshot + HTML. |
| **Adaptive test-time compute for small models** | Amaad | parked | e.g. ReVL recursive grounding, RegionFocus. Test-time compute *outside* chain-of-thought is called out as a strong differentiation area. |
| **RegionFocus as a modular plug-in** | mitigation doc | parked | Zoom into a sub-region after error detection or a VLM-judge trigger. Reported to let 7B beat 72B on grounding. |
| **Image-as-Map** | mitigation doc | parked | Encode interaction history visually (pink stars on the screenshot) rather than as text coordinates. Reported to reduce action looping and disambiguate nearby elements. |
| **Decomposed training (JEDI)** | mitigation doc | parked | Train on synthesized UI elements to give small models the background knowledge they lack. |
| **Self-correction feedback loops** | mitigation doc | parked | Model judges its own predicted point before executing; catches coordinates landing in empty regions. |

## Memory & observation

| Idea | Origin | Status | Notes |
|---|---|---|---|
| **Visual Trajectory Steering (VTS) via Memory Inception** | Abdoul | **stretch** | Decompose GUI tutorial videos → visually marked keyframes → text heuristic cards ("Step 3: click the gear icon in the top-right quadrant") → inject as **latent KV banks** into selected attention layers of a small model, not as visible prompt. Targets action looping + long-horizon memory without consuming the context window. Full proposal in Drive. **Conditional on the core pipeline being on track at the Midway checkpoint.** Risk: brittle if tutorial videos are outdated. |
| **Compressed GUI-state memory** | Raghav | parked | Give the agent a *learned GUI state* + last actions instead of raw screenshot history. Also helps with sudden ads/pop-ups: the model can see something changed without acting. |
| **Streaming visual observations** | Matt / project proposal | parked | Frame-difference summaries, compressed memory, or learned temporal representations rather than full screenshot history. Matters for scrolling, video, games, dynamic UIs, UI testing. Not solved even for frontier models. Transformers blow up on the long contexts this implies. |

## Planning & reasoning

| Idea | Origin | Status | Notes |
|---|---|---|---|
| **World models for CUA planning** | Abdoul | parked | Simulate future GUI states for strategic planning. Open problem: how does a world model know what to do in unfamiliar software? Possible answer: let it explore and generate its own training data. Constraint: simulation accuracy vs. real-time inference speed. |
| **Process-Based Reward Modeling (PRM)** | Ideation tracker | parked | Large teacher reward model scores intermediate steps. Rationale: outcome-only supervision is too sparse for small models. Challenge noted: 134+ evaluation functions needed to verify internal software state. Grounded in *Let's Verify Step by Step*. |
| **RL for best-action prediction** | Raghav | parked | Model predicts the state after each candidate action, gets nudged toward the best one; supervise the reasoning traces too. |
| **Reward efficient thinking** | Abdoul | parked | Incentivize shorter, more effective reasoning traces. Motivated by planning/reflection consuming 75–94% of task time and far more steps than needed. |
| **Instruction enhancement via LLM** | Raghav | parked → **partly active** | An LLM rewrites the task instruction with broad directions + success metrics before it reaches the CUA. **This is now directly load-bearing**: the same technique is the proposed fix for OSWorld-Human's incomplete human-step instructions. Literature reports 0% → 100% swings from instruction clarification. |
| **CALL_USER meta-action** | mitigation doc | parked | Let the agent resolve ambiguity interactively. Moderate querying (1–2 times) boosts success and user preference on underspecified tasks. Also the natural test for the Refusal/Infeasibility leaf. |

## Training data

| Idea | Origin | Status | Notes |
|---|---|---|---|
| **Train on YouTube computer-use tutorials** | Abdoul | parked | CUA-Suite already exists; also the online-video inference paper. Gemma 4 was trained for video understanding. |
| **Agentic trajectory scraping from video + synthetic augmentation** | Amaad | parked | Open question: are models good enough to model computer environments? |
| **Synthetic RL environment task generation** | Amaad | parked | — |

## Architecture & system

| Idea | Origin | Status | Notes |
|---|---|---|---|
| **Pixel-only CUA with optional code/tool use** | project proposal | parked | CodeAct-style tool use to compensate for small-model capacity: crop images, track frame changes, maintain structured memory. Open question raised repeatedly: *what are the concrete use cases?* |
| **Harness design as a research variable** | Matt | parked | Iterate the observe-plan-act loop, memory, retries, action abstraction, subgoals, self-checking. Explicitly framed as analogous to **neural architecture search** — model fixed, system searched. For small models the harness may matter as much as the weights. |
| **Fully open-source CUA (Molmo-class)** | Matt | parked | Differentiator: no reliance on closed-provenance weights. Only genuinely interesting if we can train VLMs from scratch and study how backbone properties affect downstream CUA performance. With Qwen we can't tell whether our training is redundant with its pretraining. |
| **RL training for small VLM agents** | project proposal | parked | After an imitation-learning baseline exists. |

## Experiment-design ideas (from the stress-testing plan)

Not scheduled, but a well-formed protocol worth reusing when controlled tracks
start:

- **Variable visuals** — randomized wallpapers, icon themes, browser zoom 70–150%,
  to test environment-noise robustness.
- **Ambiguity injection** — 20% of tasks made underspecified, to separate
  speculative execution from `CALL_USER`.
- **Pass^k reliability protocol** — each task run 10×; success defined as k/10, to
  account for stochasticity. *(Note: the master plan deliberately scoped this
  **out** — 369×10 only if reliability becomes its own research question.)*
- **Evaluator audit** — manually review all OSWorld evaluator scripts to remove
  hidden constraints not stated in the prompt. **This one is now urgent**, given
  the pivot.
- **Human-in-the-loop simulation** — when the agent issues `CALL_USER`, a simulated
  user supplies the missing info; measure whether success moves off 0%.
- Metrics proposed: success-rate decay curve vs. step count (locates long-horizon
  memory failure), repetition ratio (quantifies action looping), relational-vs-direct
  grounding delta, instruction–evaluator mismatch rate.

## Process ideas

| Idea | Origin | Status |
|---|---|---|
| **Hermes research-ops agent** | Abdoul | **active** (P0) — skills, cron monitoring, SSH access to clusters |
| **Auto-research agents** (Karpathy-style) — spin up agents to survey literature and brainstorm | Abdoul | parked (P3/later) |

## Closed

| Idea | Why closed |
|---|---|
| **Real-time-strategy game literature** (AlphaStar etc.) | Explored in May–June; "didn't end up going anywhere." Links retained in the Reading List. |
| **OpenTau** | Explicitly ruled out in the master plan — it is robotics VLA training, not relevant. Use OpenCUA + AgentNetBench. |

---

## Adding a new idea

The Research Ideation Tracker has a template. Fill in: **General overview**
(core mechanism + how it fits the pixel-only constraint), **Rationale** (why it
beats baseline), **Technical challenges**, **Hypothesized impact** (expected delta
on OSWorld-Verified or ScreenSpot), **Execution plan**.

If an idea graduates into its own workstream, follow
[`docs/multi_idea_stages.md`](../multi_idea_stages.md) — create `<idea>/AGENTS.md`
mirroring `errorAnalysis/`, add a row to the root `AGENTS.md` table, keep
execution out of root `ops/`.
