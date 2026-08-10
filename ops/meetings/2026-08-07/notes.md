# Meeting notes — 2026-08-07

## Attendees
- Abdoul
- Raghav
- Amaad
- Matt (mentioned but not confirmed present)

## Technologies discussed
- **Models:** UiTars-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B, Qwen3.5-VL 9B, Sonnet 4.6 (Judge)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, ScreenSpot, TheAgentCompany, WebArena
- **Compute:** Babel (L40S GPUs), PSC Bridges-2 (GPU-shared, node v016), Slurm
- **Infra:** vLLM 0.11.0 (resolved CUDA 12.6 vs. 13 incompatibility on Bridges), OpenCUA ([github.com/xlang-ai/OpenCUA](https://github.com/xlang-ai/OpenCUA))
- **Papers referenced:**
  - OSWorld-Human: [arxiv.org/pdf/2506.16042](https://arxiv.org/pdf/2506.16042)
  - Error analysis draft: [arxiv.org/pdf/2606.31270](https://arxiv.org/pdf/2606.31270)
  - TheAgentCompany: [arxiv.org/pdf/2412.14161](https://arxiv.org/pdf/2412.14161)
  - AI/Human Workflow Comparison: [arxiv.org/abs/2510.22780v2](https://arxiv.org/abs/2510.22780v2)
  - OSWorld-G: [arxiv.org/pdf/2505.13227](https://arxiv.org/pdf/2505.13227)
  - GUI-Perturbed: [arxiv.org/pdf/2604.14262](https://arxiv.org/pdf/2604.14262)
  - CUA-Suite (video demos): [arxiv.org/abs/2603.24440](https://arxiv.org/abs/2603.24440)
  - Stable Diffusion 3: [arxiv.org/pdf/2403.03206](https://arxiv.org/pdf/2403.03206)
  - Qwen3-VL Technical Report: [arxiv.org/pdf/2511.21631](https://arxiv.org/pdf/2511.21631)
- **Pixel Agent repo:** [github.com/MaximusAnax/pixel_agent](https://github.com/MaximusAnax/pixel_agent)

## Decisions made
- Use **vLLM 0.11.0** as the lab-standard version on Bridges (resolves CUDA library mismatch)
- Keep OSWorld VMs and inference both on Babel/Bridges (not split with AWS)
- Judge pipeline: use a VLM judge given the reference trajectory, predicted trajectory, OSWorld metric (0–1), and evaluator test output to classify failure modes
- CUA agent: Qwen3.5-VL 0.8B; Judge: Qwen3.5-VL 9B on Babel L40S GPUs
- Cost threshold: if frontier-model error analysis costs ≤ $25, proceed without checking in with Matt; if more, check in first
- Website updated combining Abdoul's and Raghav's trajectory viewers
- Ran OSWorld with OSWorld-Human dataset as guide using UiTars-72B → **60/361 tasks succeeded**

## Feedback / critiques
- **OSWorld-Human incomplete steps** cause failures: e.g., instructions say to type in a search bar but never say to press Enter
- **Model races ahead** while screen is still loading from the previous action
- **OSWorld initialization errors**: initial environment not loaded properly (e.g., Chrome not opened on setup)
- Benchmark drift concern: websites/software drift over time, invalidating trajectories
- Relevance concern: frontier models evaluated on OSWorld v2.0 — is the benchmark still meaningful for small models?

## Ideas considered
- Give the Judge both agent and human trajectory; ask it to select **all applicable failure modes** (rather than primary/secondary classification only)
- "Oracle Agent" that replays human actions in OpenCUA to generate a screenshot for every human step
- Run OSWorld with a frontier model that reads OSWorld-Human notes → check if it achieves ~100%; diagnose why not
- Generate grounding labels with an image diffusion model (Stable Diffusion 3); detect generated marker via traditional CV or a highly unusual synthetic pattern (e.g., houndstooth)
- World models for planning in CUA; allow world model to explore new software and self-generate training data
- Screenshot generation as a grounding method
- Use YouTube computer-use tutorial videos as training data (cf. Gemma 4 video training)
- Reward **efficient** thinking traces to reduce unnecessary planning steps
- Compress GUI state history into a learned representation rather than raw screenshots, to handle pop-ups/ads and long-horizon context
- Separate perception from planning: one model for candidate element selection, another for action output (potentially a third for tool calls / web search)
- RL to teach best action by predicting post-action state; supervise reasoning traces
- Special "call another model" action: main VLM acts, specialist VLM grounds/creates bounding boxes on demand
- LLM instruction enhancer: expand original task instruction with broad directions and success metrics before agent execution
- Agentic trajectory scraping from videos + synthetic augmentation to create new traces
- Synthetic RL environment task generation
- Auto-research setup (Karpathy-style): agents spin up to explore literature and brainstorm (P3 / later)

## Ideas & research directions
- **OSWorld error analysis** — primary near-term focus; identify perception/grounding errors vs. cognitive/planning errors
- **Release proper OSWorld-Human dataset** with full trajectories (blocked by benchmark drift concern)
- **Better CUA — generation-based** (e.g., diffusion grounding)
- **Better CUA — small model** (pixel-only, laptop/edge-scale)
- **Inter-annotator agreement study**: Abdoul vs. Raghav vs. Judge (Sonnet 4.6) on 10 manually selected traces; compute human–human and human–judge agreement
- **Process Reward Models** (step-level verification): OSWorld-Verified + "Let's verify step by step"
- **Adaptive test-time compute** for small models (e.g., ReVL recursive grounding approach)
- **Fully open-source CUA**: differentiate from Qwen-based work by using fully open-provenance backbone (e.g., Molmo)
- **Other benchmarks** to check for existing error analysis: TheAgentCompany, WebArena (may have human trajectories), OSWorld-G

## Action items
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: HumanAgent succeeded, OpenCUA-3B and 7B both failed, and Judge produced a failure-mode conclusion
- [ ] @Abdoul — Read the space of other benchmarks (besides OSWorld) and determine whether existing error analysis would make our error analysis non-novel
- [ ] @Abdoul — Write up Babel quick-start guide (GPU queues, env setup on remote machine)
- [ ] @Abdoul — Make an SSH key for Babel/Bridges that the Hermes agent can use
- [ ] @Abdoul — Set up cron jobs to monitor experiments
- [ ] @Abdoul — Run failure analysis using pre-made prompt
- [ ] @Raghav — Dive deeper into the Human Agent; find a method to transform human trajectories into more accurate instructions that raise Human Agent success rate
- [ ] @Raghav — Investigate initialization bugs / OSWorld hanging states (e.g., why Chrome is not opened on setup)
- [ ] @Raghav — Manually annotate the agreed-upon set of ~10 traces (one OpenCUA model)
- [ ] @Abdoul — Manually annotate the same set of ~10 traces; compare with Raghav and Judge for inter-annotator agreement
- [ ] @Abdoul — Aim for first full run of OpenCUA on Babel
- [ ] @Amaad — Set up Hermes Agent; create `Skill.md` for onboarding a new idea, including instructions for accessing/updating meeting docs via Google Workspace CLI; share with team
- [ ] @Amaad — After trajectories are collected, ask an agent to estimate frontier-model error-analysis cost (input/output tokens); proceed if ≤ $25, check with Matt if more

## Open questions
- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for running OpenCUA on Bridges?
- Should OSWorld VMs run locally/AWS while inference stays on Bridges/Babel? *(Decided: keep everything on Bridges/Babel — but worth confirming)*
- Is OSWorld still a relevant benchmark now that frontier models are evaluated on v2.0? Is error analysis only valuable for small models?
- If we run OSWorld with a frontier model that sees the OSWorld-Human notes, do we get ~100% success? If not, why not?
- What is the SOTA for small models on GUI grounding and on pixel-based computer use?
- How do we definitively distinguish perception/grounding errors from cognitive/planning errors in automated analysis?
- What counts as "small" for this project — 0.8B? 3B? 7B? 9B?
- Do we care about open-weights (QwenVL) vs. fully open-source (Molmo) distinction, and should that differentiate the work?
