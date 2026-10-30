# Meeting notes — 2026-10-30

## Attendees
*(Not explicitly listed for the 2026-10-30 session)*

## Technologies discussed
- **Models:** OpenCUA-3B, OpenCUA-7B, UiTars-72B (grounding), Sonnet-4.6 (judge), Qwen3.5-VL 0.8B / 9B, Claude Opus 5
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, ScreenSpot V2, WebArena, VisualWebArena, ClawBench, A3/AITK, OmniGUI, VideoCUA/CUA-Suite, UI-Vision, Mind2Web, WebLINX, AITW, WebChain, PC Agent-E
- **Compute:** Babel (L40S GPUs), PSC Bridges-2 (`cis260099p`, GPU-shared), Slurm; vLLM 0.11.0 confirmed working on Bridges-2 under CUDA 12.6
- **Frameworks:** OSWorld evaluation harness, OpenCUA repo, vector/text database (proposed), LangGraph, Anthropic Agent SDK
- **Datasets:** OSWorld-Human (`https://github.com/WukLab/osworld-human`), HuggingFace OpenCUA trajectories
- **Papers cited:**
  - CUADebug `arXiv:2608.02643`
  - OSWorld-Human `arXiv:2506.16042`
  - Error analysis paper `arXiv:2606.31270`
  - How benchmarks mis-score `arXiv:2607.28367`
  - TheAgentCompany `arXiv:2412.14161`
  - AI Agents vs. Human Workflows `arXiv:2510.22780`
  - OSWorld-G `arXiv:2505.13227`
  - CUA-Suite `arXiv:2603.24440`
  - GUI-Perturbed `arXiv:2604.14262`
  - ClawBench `arXiv:2604.08523`
  - A3/AITK `arXiv:2501.01149`
  - OmniGUI `arXiv:2605.18758`
  - WebChain `arXiv:2603.05295`
  - PC Agent-E `arXiv:2505.13909`
  - UI-Vision `arXiv:2503.15661`
  - AITW `arXiv:2307.10088`
  - Qwen3-VL Technical Report `arXiv:2511.21631`
  - *Beyond the Final Answer* (tool-augmented agent reasoning trajectories)
  - *Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding*
  - *Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs*
  - Stable Diffusion 3 `arXiv:2403.03206`

## Decisions made
- Use **vLLM 0.11.0** on Bridges-2 with CUDA 12.6; this is the confirmed lab-standard configuration
- Keep OSWorld VMs and inference both on Bridges/Babel (not split with AWS)
- Use **Babel** for L40S GPUs; use different models for agent vs. judge (e.g., Qwen3.5-VL 0.8B as agent, Qwen3.5-VL 9B as judge)
- Judge will receive: reference (human/gold) trajectory, predicted trajectory, OSWorld metric score, and evaluator test output
- Priority benchmark tiers for human ↔ agent comparison:
  - **Tier 1:** OSWorld-Human, WebArena, VisualWebArena, ClawBench, A3
  - **Tier 2:** OmniGUI, VideoCUA/CUA-Suite, WebChain, Mind2Web, WebLINX, AITW, UI-Vision, PC Agent-E
- UiTars-72B run on OSWorld produced **60/361 tasks** successful; multiple error categories identified (incomplete human steps, screen-load timing, initialization failures)
- Sonnet-4.6 is the current judge over OpenCUA-3B and OpenCUA-7B traces; OSWorld-Human not yet folded in
- Amaad is departing to `withampersand.ai`; Matt will recruit two new project members

## Feedback / critiques
- OSWorld-Human instructions are sometimes incomplete (e.g., instructs model to type in a search bar but never to press Enter), reducing gold trajectory reliability
- Screenshots alone are not helping error analysis — **text descriptions of steps** are more informative (Raghav)
- Gold trajectories only help when the gold diverges from the agent trajectory at the exact moment of error
- Human annotators are sometimes wrong: one case where the model correctly clicked despite an incorrect referential expression — LLM judge called it a "reasoning" error; human annotator called it a "grounding" error
- OSWorld may be losing relevance for frontier models if those models have very few errors; more relevant to small models
- Websites/software drift means a released OSWorld-Human dataset with actual trajectories would degrade over time
- Historical screenshots in context can confuse the model even with action history included; unclear if current VLMs are trained to understand sequential frames

## Ideas considered
- **Subgoal analysis:** Break gold and agent trajectories into subgoals; judge whether the agent completed each subgoal (even via a different path); use topological ordering (flagged as extremely tricky — hard to test, relies on agent knowledge of UIs)
  - Edge case: tasks with no meaningful subgoals (e.g., "Open most recently closed tab" via Ctrl+Shift+T)
  - Fallback: use agent's own reasoning subgoals when gold provides no useful structure
- **Image diffusion model for GUI grounding:** Use Stable Diffusion 3 to mark up screenshots; use highly unusual patterns (e.g., houndstooth) that don't appear in standard UIs but are easy for diffusion models to generate; detect marks via traditional CV
- **System One (Jev) model exploration:** Use fast/cheap System One model to explore many possible trajectory paths (beam search, stochastic beam search, backtracking) for richer error analysis or task solving; Jev now has a bounding box API
- **Multi-subagent exploration with shared memory:** Dispatch multiple subagents to explore different UI paths; store exploration in a vector/text database for future reuse; use multiple Chrome instances to avoid side-effect contamination — analogous to coding agents reading a large codebase in parallel, but materially different because UI interactions have side effects
- **Oracle Agent:** Run human OSWorld-Human action sequences inside the OpenCUA harness to generate per-step screenshots for side-by-side comparison with AI traces
- **Frontier model as gold-trajectory generator:** Provide OSWorld-Human notes to a frontier model to generate trajectories; target 100% success rate as the gold standard
- **ReVL / recursive grounding** for small models as adaptive test-time compute
- **Dual-model perception/planning split:** One small model for candidate selection (perception), a second for action output (planning); optionally a third for tool calls (e.g., documentation lookup)
- **Learned GUI state compression for memory:** Compress GUI state rather than passing raw screenshots as history; could handle sudden ads/pop-ups by comparing compressed states
- **RL with predicted state supervision:** Train model to predict post-action state, reward best action selection, supervise reasoning traces
- **Instruction enhancement via LLM:** Have an LLM expand the original task instruction with broad directions and success metrics before passing to the CUA
- **YouTube tutorial training data:** Train on computer-use tutorial videos (cf. *Learning from Online Videos at Inference Time for Computer Use Agents*)

## Ideas & research directions
- **Primary research goal (error analysis paper):** Create a reusable framework for automated CUA error analysis using gold/human trajectories; answer: *How much do gold trajectories improve automated error analysis, and what trajectory properties drive that improvement?*
- **Judge design:** Ask judge to select *all* applicable failure modes (not just primary/secondary) from a predefined taxonomy, given both agent and human trajectories
- **Inter-annotator agreement study:** Raghav and Abdoul both manually annotate the same set of failures from one OpenCUA model; compute agreement between (human A / human B), (human A / judge), (human B / judge)
- **Streaming visual observation for CUAs:** Compressed memory or frame-difference summaries to handle scrolling, video, games, and dynamic UIs — not yet solved even for frontier models
- **Pixel-only small VLM agent:** Full training + harness pipeline (imitation learning → RL); evaluate on edge/laptop-scale inference; explore whether code/tool use can compensate for limited model capacity
- **AI-assisted idea generation methodology:** Critique a specific paper → ask what would be improved; refine a specific idea across 10 variants; identify 10 closest related papers and assess novelty impact
- **Auto-research agent (P3/later):** Spin up agents to survey literature and brainstorm (cf. Andrej Karpathy's auto-research concept)

## Action items
- [ ] @Raghav — Dive deeper into OSWorld-Human; find a method to transform human trajectories into more accurate instructions that yield higher human-agent success rate
- [ ] @Raghav — Investigate and fix initialization bugs / OSWorld benchmark issues causing hanging states (e.g., Chrome not opened on setup)
- [ ] @Raghav — Finish gathering human-trajectory screenshots from OSWorld-Human dataset via benchmark environment and merge into repo
- [ ] @Raghav — Manually annotate a pilot set of ~10 traces (path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`)
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks meeting all criteria: human agent succeeded; OpenCUA-7B and 3B both failed; judge produced failure-mode conclusions
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Manually annotate the same pilot set of ~10 traces; compute inter-annotator agreement with Raghav and with the judge
- [ ] @Abdoul — Read failure analysis papers to survey existing failure categorization approaches
- [ ] @Matt — Give OpenAI API access to the team
- [ ] @Matt — Meet with two additional potential project members
- [ ] **Team** — Update OSWorld evaluation script to surface per-trace success/failure information (include task description JSON + evaluator function definitions, e.g., `is_expected_tabs` from `desktop_env/evaluators/metrics`) and expose this to both human reviewers and the judge
- [ ] **Team** — Make OSWorld-Human traces visible alongside OpenCUA traces in the annotation viewer
- [ ] **Team** — Build an Oracle Agent that replays human OSWorld-Human actions inside OpenCUA to generate per-step screenshots
- [ ] **Team** — Consolidate annotation viewer features (from Raghav's and Abdoul's separate HTML tools) into one canonical tool with: task ID display, canonical task order, real task description from JSON, multi-label failure mode support, large image zoom on click, thinking trace + action display, side-by-side AI/human trace view, collapsible reasoning trace, left-hand navbar with category/prompt/step count, "failing step" integer field

## Open questions
- Does subgoal analysis (with topological ordering) remain feasible given available data, or must it rely entirely on the agent's own reasoning?
- What happens when a gold trajectory has no meaningful subgoals (e.g., single-shortcut tasks)?
- Has anyone already answered: *Do gold trajectories improve automated CUA error analysis, and which trajectory properties matter most?*
- Is OSWorld still relevant as a benchmark given that frontier models have low error rates on it?
- What is the lab-standard conda environment name, CUDA module, and vLLM version/wheel for Bridges-2?
- Should OSWorld VMs ever run on AWS, or should everything remain on Bridges/Babel?
- Do CUAs perform worse when given screenshot history as context, and if so, why? Are current VLMs even trained on sequential frame understanding?
- What is current SOTA for small models (≤7B) on GUI grounding benchmarks, and on pixel-based computer use?
- Is "small" defined as ≤2B, ≤4B, or ≤7B for this project's purposes?
- Should the project distinguish "open weights" (e.g., QwenVL) from "fully open source" (e.g., Molmo), and does that distinction affect novelty?
- Could multiple Chrome instances fully isolate side effects during multi-subagent UI exploration?
- At what cost threshold should the team check in with Matt before running frontier-model error analysis (proposed threshold: proceed if ≤$25, check in if more)?
