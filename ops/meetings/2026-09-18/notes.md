# Meeting notes — 2026-09-18

## Attendees

*(Not specified for 2026-09-18 session)*

## Technologies discussed

**Cluster / Compute**
- Babel (L40S GPUs, Andrew IDs)
- PSC Bridges-2 (`cis260099p`, GPU-shared, node v016; CUDA 12.6)
- Slurm
- vLLM 0.11.0 (workaround for CUDA 12.6 / libcudart.so.13 incompatibility on Bridges-2)

**Models**
- UiTars-72B (grounding model; 60/361 OSWorld tasks succeeded)
- OpenCUA-3B, OpenCUA-7B
- Qwen3.5-VL 0.8B (proposed CUA agent)
- Qwen3.5-VL 9B (proposed judge)
- Claude Sonnet 4.6 (current judge over traces)

**Benchmarks & Datasets**
- OSWorld / OSWorld-Human (`https://arxiv.org/abs/2506.16042`)
- OSWorld-G (`https://arxiv.org/pdf/2505.13227`)
- ScreenSpot V2
- WebArena & VisualWebArena (human Playwright traces)
- ClawBench (`https://arxiv.org/abs/2604.08523`)
- A3 / AITK (`https://arxiv.org/abs/2501.01149`)
- VideoCUA / CUA-Suite (`https://arxiv.org/abs/2603.24440`)
- WebChain (`https://arxiv.org/abs/2603.05295`)

**Papers referenced**
- CUADebug: `arXiv:2608.02643`
- How benchmarks mis-score: `arXiv:2607.28367`
- Beyond the Final Answer (tool-augmented agent reasoning trajectories)
- OSWorld-Human: `arXiv:2506.16042`
- Error analysis: `arXiv:2606.31270`
- Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding
- Stable Diffusion 3: `arXiv:2403.03206`

**Repos**
- OpenCUA: `https://github.com/xlang-ai/OpenCUA`
- pixelAgent: `https://github.com/MaximusAnax/pixel_agent`
- OSWorld evaluators/metrics: `https://github.com/xlang-ai/OSWorld/tree/main/desktop_env/evaluators/metrics`

## Decisions made

- Use **vLLM 0.11.0** on Bridges-2 as the lab-standard workaround for the CUDA 12.6 incompatibility
- Keep OSWorld VMs and inference **all on Bridges / Babel** (not split with AWS)
- Use **separate models** for agent and judge: CUA = Qwen3.5-VL 0.8B; Judge = Qwen3.5-VL 9B on Babel L40S
- Judge should receive **both agent and human trajectories** and select **all applicable failure modes** (not just primary/secondary)
- Pilot inter-annotator agreement study: both Raghav and Abdoul manually annotate the same set of traces, then compare human-A / human-B / judge agreement
- Canonical task set and order to be fixed before further annotation runs

## Feedback / critiques

- OSWorld-Human instructions are **incomplete** (e.g. instruct model to type in search bar but never press Enter), causing UiTars-72B gold-label runs to fail
- Model advances to the next action **while the screen is still loading**, producing spurious failures
- **OSWorld initialization errors**: initial environment not loaded properly (e.g. Chrome not opened on setup)
- UiTars-72B achieved only **60/361 tasks** — many failures stem from benchmark/harness issues rather than model errors
- CUADebug (`arXiv:2608.02643`) is very similar to the group's error-analysis direction; novelty must be grounded in use of human/gold trajectories

## Ideas considered

- Transform OSWorld-Human notes into more accurate step-by-step instructions to raise human-agent success rate
- Generate **gold-standard trajectories** by feeding human notes to a frontier model and requiring 100 % success rate
- Mark up screenshots using an **image diffusion model** (e.g. Stable Diffusion 3) to aid grounding; find generated markers via traditional CV or highly unusual patterns (e.g. houndstooth)
- Use a **world model** for CUA planning, letting it explore new software to generate its own training data
- **Reward efficient thinking** to reduce unnecessary steps in long-horizon tasks
- Give agents **compressed GUI state** (not raw screenshots) as memory to handle pop-ups and context drift
- **Two-model pipeline**: one model for candidate UI element selection (perception), one for action output (planning)
- RL to teach the model to predict post-action state and choose the best action; supervise reasoning traces
- **Instruction enhancement**: LLM rewrites the task instruction with broad directions and success metrics before the agent acts
- Cost estimate: after trajectories are collected, ask an agent to compute frontier-model judge cost from token counts; proceed without approval if ≤ $25

## Ideas & research directions

- **Oracle Agent**: run OSWorld in OpenCUA, replaying human actions step-by-step to generate a screenshot per step (needed for side-by-side viewer)
- **Auto-research agent** (P3 / later): spin up agents that survey literature and brainstorm, inspired by Andrej Karpathy's auto-research concept
- Use YouTube computer-use tutorials as training data for CUAs (cf. *Learning from Online Videos at Inference Time for Computer-Use Agents*)
- Explore **video-understanding backbones** (e.g. Gemma 4) instead of single-frame VLMs for sequential screenshot context
- Investigate whether CUAs perform *worse* when given screenshot history, and diagnose why
- **Adaptive test-time compute** for small models (e.g. ReVL recursive grounding) as differentiation beyond chain-of-thought

## Action items

- [ ] @Raghav — Find a method to transform human OSWorld-Human trajectories into more accurate instructions that raise human-agent success rate
- [ ] @Raghav — Investigate and fix initialization bugs / hanging states (e.g. why Chrome is not opened on setup)
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human and merge into repo
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks meeting: human-agent succeeded, OpenCUA-3B and 7B both failed, judge made a failure-mode conclusion
- [ ] @Abdoul — Continue editing HTML viewer and judge logic to incorporate both human and model screenshots per step
- [ ] @Abdoul — Refine taxonomy discovery labels starting from pilot path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- [ ] @Abdoul — Read failure-analysis papers to survey existing failure categorization schemes
- [ ] @Matt — Give OpenAI API access to team members
- [ ] @Raghav + @Abdoul — Each manually annotate the same ~10 pilot traces; compute pairwise inter-annotator agreement (human/human, human/judge-with-gold, human/judge-without-gold)
- [ ] @Raghav + @Abdoul — Agree on a common data format for sharing trajectories

**Viewer / tooling (no single owner specified)**
- [ ] OSWorld evaluation script to emit structured success/failure metadata visible to humans and passed to the judge (include task JSON + evaluator function source, e.g. `is_expected_tabs`)
- [ ] Build **Oracle Agent** in OpenCUA to replay human actions and capture per-step screenshots
- [ ] Consolidate HTML annotation tools (Raghav's + Abdoul's) into one viewer with: task ID, canonical task order, real task description, multiple ordered failure modes, large image on click, thinking trace (collapsed by default), action taken (always shown), side-by-side AI vs. human trace, left-nav with category/prompt/step count, failing-step integer field for human annotation

## Open questions

- Do we have the ability to bulk-download human reference runs from ClawBench and A3 before committing to those benchmarks?
- Has anyone already answered: *how much do gold/human trajectories improve automated error analysis, and what trajectory properties drive that improvement?*
- Is OSWorld still relevant given that frontier models are now evaluated on OSWorld v2.0 and small-model errors may differ fundamentally?
- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for serving OpenCUA on Bridges-2?
- Should OSWorld VM environments run locally / on AWS while inference runs on Bridges / Babel, or keep everything on Bridges/Babel? *(Tentative decision: keep on Bridges/Babel)*
- How should failure-mode priority be determined: by step of occurrence, downstream impact, or a custom prioritization function?
