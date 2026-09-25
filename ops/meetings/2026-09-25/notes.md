# Meeting notes — 2026-09-25

## Attendees
- Raghav, Abdoul, Amaad, Matt (implied by action items)

## Technologies discussed
- **Models:** UiTars-72B (grounding), OpenCUA-3B, OpenCUA-7B, Sonnet-4.6 (judge), Qwen3.5-VL 0.8B / 9B, frontier models (Opus 5)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, WebArena, VisualWebArena, ClawBench, A3/AITK, ScreenSpot V2
- **Clusters:** Babel (L40S GPUs), PSC Bridges-2 (Slurm, CUDA 12.6.1), vLLM 0.11.0
- **Datasets:** OSWorld-Human (`WukLab/osworld-human`), WebArena/VisualWebArena Playwright traces, WebChain, VideoCUA / CUA-Suite, Mind2Web, WebLINX, AITW, OmniGUI, UI-Vision, PC Agent-E, Android in the Wild
- **Frameworks:** BrowserGym, LangGraph, Anthropic/Google ADK
- **Papers referenced:**
  - CUADebug [arXiv:2608.02643]
  - OSWorld-Human [arXiv:2506.16042]
  - Error analysis [arXiv:2606.31270]
  - How benchmarks mis-score [arXiv:2607.28367]
  - CUA-Suite / VideoCUA [arXiv:2603.24440]
  - OSWorld-G [arXiv:2505.13227]
  - GUI-Perturbed [arXiv:2604.14262]
  - ClawBench [arXiv:2604.08523]
  - A3 [arXiv:2501.01149]
  - OmniGUI [arXiv:2605.18758]
  - WebChain [arXiv:2603.05295]
  - PC Agent-E [arXiv:2505.13909]
  - Qwen3-VL Technical Report [arXiv:2511.21631]
  - Stable Diffusion 3 [arXiv:2403.03206]
  - Memory Inception (latent-space KV cache manipulation)
  - Beyond the Final Answer (tool-augmented agent reasoning trajectories)
  - Learning from Online Videos at Inference Time for Computer-Use Agents

## Decisions made
- **Bring a new person into the project** — agreed unanimously.
- **Infrastructure:** Keep OSWorld VMs and inference both on Bridges/Babel (not split to AWS).
- **vLLM version lock:** Use vLLM 0.11.0 on Bridges (CUDA 12.6); avoids `libcudart.so.13` mismatch from newer wheels.
- **Judge model:** Sonnet-4.6 over traces from OpenCUA-3B and OpenCUA-7B; OSWorld-Human not yet folded in to judge pipeline.
- **Benchmark priority (Tier 1):** OSWorld-Human, WebArena human trajectories, VisualWebArena human trajectories, ClawBench, A3 — these support direct human ↔ agent comparison.
- **Paper framing:** Novelty relative to CUADebug is use of human/gold trajectories in the judge; CUADebug is considered concurrent work (post-March 1 2025) so comparison is not required for NeurIPS.
- **Cost gate:** If frontier-model error analysis run costs ~$25 or less, proceed without checking with Matt; if more, check in first.
- **Pilot annotation set:** Use `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv` as the starting point for manual annotation.

## Feedback / critiques
- OSWorld-Human instructions are incomplete — e.g., steps tell the model to type in a search bar but never instruct it to press Enter, causing the human agent to stall.
- Model moves to the next action while the screen is still loading from the previous action, producing spurious failures.
- OSWorld initialization errors: the initial environment sometimes not loaded properly (e.g., Chrome not opened on setup).
- UiTars-72B human-agent run achieved only 60/361 tasks (≈17%), partly due to the above OSWorld-Human instruction gaps.
- OSWorld-Human dataset risk: websites/software will drift, making trajectories invalid over time.
- Concern that OSWorld may be less relevant if frontier models have few errors there — analysis would mainly apply to small models.
- Historical screenshots in context can confuse the model even when action history is included; unclear whether any current model was trained to understand sequences of video frames.

## Ideas considered
- **Multi-agent parallel exploration:** Dispatch multiple subagents to explore different UI paths simultaneously; store results in a vector/text DB so future tasks in the same UI are cheaper. Use separate Chrome instances to avoid side-effects. Analogy: coding agents dispatched to read different parts of a codebase, but CUA exploration is not side-effect-free. Trade-off: higher cost/latency vs. better coverage.
- **Oracle agent:** Run a human-trajectory replay inside OpenCUA to generate screenshots for every human step, enabling side-by-side comparison with AI trace.
- **Gold trajectory generation from notes:** Feed OSWorld-Human natural-language notes to a frontier model as it executes the task; require 100% success rate to qualify as gold.
- **Image-diffusion-based grounding markup:** Use a diffusion model (e.g., Stable Diffusion 3) to annotate a screenshot with a highly unusual pattern (e.g., houndstooth) at the click target; recover the location via traditional CV or pattern detection. (Provisional — feasibility unclear.)
- **Compressed GUI state / learned memory:** Instead of passing raw screenshot history, compress GUI state and pass it alongside recent actions; could help with pop-ups and ads by detecting state changes without extra actions.
- **Dual-model perception + planning split:** Separate candidate-selection model (grounding) from action-output model (planning); optionally add a third model for tool calls (e.g., web search for documentation).
- **RL for best-action prediction:** Train model to predict state after candidate actions and reward the best choice; supervise reasoning traces.
- **Instruction enhancement agent:** Use an LLM to enrich the original task instruction with broad-level directions and success metrics before passing to the CUA.
- **Rewarding efficient thinking:** Reward concise, effective reasoning traces to reduce unnecessary steps in planning/reflection phases.
- **World models for CUA planning:** Allow a world model to explore new software and generate its own training data; unclear how it generalises to novel apps.
- **YouTube tutorial training:** Train on video walkthroughs of computer use tasks (VideoCUA / CUA-Suite already covers large-scale human video demos).
- **Auto-research agent (Karpathy-style):** Spin up agents to survey literature and help brainstorm; flagged as P3/later.
- **Synthetic data augmentation:** Agentic trajectory scraping from videos + synthetic augmentation; rely on paired screenshot + HTML data or orthogonal sources (app documentation, alt text) to improve icon understanding.
- **Adaptive test-time compute for small models:** e.g., ReVL recursive grounding approach; test-time compute beyond chain-of-thought as a differentiator for small-model work.

## Ideas & research directions
- **Core research question:** How much do successful (gold) trajectories improve automated LLM-as-judge error analysis of a CUA? What properties of those trajectories drive the improvement?
- **Error analysis pipeline:**
  1. Obtain gold trajectories (human or frontier-model-from-notes).
  2. Run an offline model (OpenCUA-3B/7B) to produce AI trajectories.
  3. Evaluate AI trajectories on the benchmark (success rate).
  4. LLM-as-judge error analysis *with* gold trajectories.
  5. LLM-as-judge error analysis *without* gold trajectories.
  6. Human annotation on a sampled subset; compute inter-annotator agreement (human/human, human/judge+gold, human/judge−gold, judge+gold/judge−gold).
- **Failure-mode taxonomy refinement:** Consider prioritising failure modes by step of occurrence (earlier = higher impact), by downstream cascading impact, or by a custom priority function.
- **Streaming visual observation:** Fixed-frame perception misses temporal information (scrolling, video, dynamic UIs); compressed memory or frame-difference summaries may be needed; not solved even for frontier models.
- **Pixel-only small VLM agent training:** RL or imitation learning from demonstrations; iterating on harness design (observe → plan → act loop, memory, retries, action abstraction) is analogous to NAS.

## Action items
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: human agent succeeded, OpenCUA-7B and -3B both failed, and the judge already produced a failure-mode conclusion.
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace.
- [ ] @Abdoul — Read failure-analysis papers to survey existing failure categorisation schemes.
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human; merge into repo.
- [ ] @Raghav — Find a method to transform human trajectories into more accurate instructions (higher human-agent success rate).
- [ ] @Raghav — Investigate and fix OSWorld initialization bugs / hanging states (e.g., Chrome not opened on setup).
- [ ] @Raghav — Manually annotate the pilot set of ~10 traces (path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`).
- [ ] @Abdoul — Manually annotate the same ~10 pilot traces; compute inter-annotator agreement with Raghav and with the judge.
- [ ] @Matt — Provide OpenAI API access to the team.
- [ ] @Amaad — For each Tier-1 benchmark identified, determine exactly what exists in each human trajectory (real actions vs. natural-language notes).
- [ ] All — OSWorld evaluation script should output pass/fail reasoning visible to humans and fed to the judge, including the task JSON and relevant evaluator metric functions (e.g., `is_expected_tabs` from `desktop_env/evaluators/metrics`).
- [ ] All — Build an "Oracle Agent" that replays human OSWorld-Human actions inside OpenCUA to generate a screenshot for every human step.
- [ ] All — Consolidate annotation viewer features (Raghav's + Abdoul's HTML tools) into one tool; requirements: task ID display, canonical task order, real task description from JSON, multiple ordered failure modes, large-image click-to-zoom, thinking trace (hidden by default, click to reveal), action always shown, side-by-side AI + human traces, left-nav with category/prompt/step count, failing-step integer field.
- [ ] All — After obtaining full trajectory data, have an agent estimate frontier-model error-analysis cost (input/output tokens); proceed if ≤ $25, else check with Matt.

## Open questions
- Is OSWorld still a relevant benchmark given that frontier models have few errors on it — is the analysis only useful for small models?
- Does giving a VLM screenshot history actually hurt performance, and if so, why? Are any current models trained to understand sequences of frames?
- Is there existing work that answers "how much do gold trajectories improve automated error analysis?" (ref: *Beyond the Final Answer* paper covers the no-gold-trace case).
- How should failure modes be prioritised — by step of occurrence, cascading downstream impact, or a custom function?
- What is the SOTA for small models (≤7B) on GUI grounding (ScreenSpot V2, OSWorld-G) and on pixel-based computer use (OSWorld-Verified)?
- What constitutes "small" for this project — 0.8B, 2B, 4B, 7B?
- Should the project pursue open-weights (QwenVL) or fully open-source (Molmo) models, and does that distinction matter for novelty?
- Can the OSWorld-Human natural-language notes reliably produce 100%-success gold trajectories when fed to a frontier model — if not, why not?
- Should we verify bulk-download availability of ClawBench human reference runs before committing to that benchmark?
- Are the ~300 A3 human trajectories available as a standalone downloadable archive?
