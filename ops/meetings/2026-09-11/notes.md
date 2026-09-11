# Meeting notes — 2026-09-11

## Attendees

- Abdoul
- Raghav
- Amaad (likely present based on context)
- Matt (referenced but unclear if present)

---

## Technologies discussed

- **Models:** OpenCUA-3B, OpenCUA-7B, UiTARS-72B (grounding), Sonnet-4.6 (judge), Qwen3.5-VL 0.8B / 9B, frontier models (Opus 5)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, ScreenSpot V2, WebArena, VisualWebArena, ClawBench, A3/AITK, WebChain, Mind2Web, WebLINX, AITW, VideoCUA/CUA-Suite, OmniGUI, UI-Vision, PC Agent-E
- **Clusters:** Babel (L40S GPUs), PSC Bridges-2 (CUDA 12.6), Slurm
- **Infra:** vLLM 0.11.0 (resolved CUDA 12.6 vs. 13 mismatch), Playwright traces, BrowserGym
- **Papers cited:**
  - CUADebug [arXiv:2608.02643]
  - OSWorld-Human [arXiv:2506.16042]
  - Error analysis paper [arXiv:2606.31270]
  - How benchmarks mis-score [arXiv:2607.28367]
  - CUA-Suite / VideoCUA [arXiv:2603.24440]
  - ClawBench [arXiv:2604.08523]
  - A3/AITK [arXiv:2501.01149]
  - OmniGUI [arXiv:2605.18758]
  - AITW [arXiv:2307.10088]
  - WebChain [arXiv:2603.05295]
  - PC Agent-E [arXiv:2505.13909]
  - OSWORLD-G [arXiv:2505.13227]
  - Qwen3-VL [arXiv:2511.21631]
  - GUI-Perturbed [arXiv:2604.14262]
  - *Beyond the Final Answer* (tool-augmented agent reasoning trajectories)
  - *Learning from Online Videos at Inference Time for Computer-Use Agents*

---

## Decisions made

- **vLLM version on Bridges-2:** Use vLLM **0.11.0** (resolves CUDA 12.6 vs. 13 mismatch; avoid 0.12.0 and 0.23)
- **Keep everything on Bridges/Babel** — OSWorld VMs should not be split to AWS
- **Judge model:** Sonnet-4.6 over OpenCUA traces (3B and 7B)
- **CUADebug is concurrent work** (published July 31); NeurIPS policy exempts papers after March 1 2025 from required comparison — our novelty angle is using human/gold trajectories in the judge
- **Tier 1 benchmarks** for human ↔ agent comparison: OSWorld-Human, WebArena, VisualWebArena, ClawBench, A3
- **Judge should receive:** reference trajectory, predicted trajectory, OSWorld metric score, and evaluator test output (including evaluator function definitions, e.g. `is_expected_tabs`)
- **Cost threshold:** if full frontier-model error analysis run costs ~$25 or less, proceed without checking with Matt; check in if more expensive

---

## Feedback / critiques

- OSWorld-Human instructions are **incomplete** — e.g. human steps tell the model to type in a search bar but never instruct it to press Enter, causing agent failures that are not true model errors
- UiTARS-72B achieves only **60/361 tasks** (≈17%) using OSWorld-Human as a guide, indicating gold-label generation is non-trivial
- OSWorld **initialization bugs** cause hanging states (e.g. Chrome not opened on setup); these corrupt trajectory data before the agent even acts
- Agent moves to the next action **while the screen is still loading** from the prior action — a timing/synchronization error distinct from model capability failures
- Historical screenshots in context can **confuse the model** even when action history is included; unclear if current VLMs are trained to understand sequences of frames
- Frontier models are now evaluated on **OSWorld v2.0**, raising the question of whether original OSWorld is still a relevant evaluation target for this work
- Icon grounding accuracy (21–72%) is the **main differentiator** between models; text grounding is relatively saturated (70–82%)

---

## Ideas considered

- **Oracle Agent:** run in OpenCUA harness, replay human actions from OSWorld-Human to generate a screenshot per human step — enables side-by-side human vs. agent trajectory comparison
- **Multi-failure-mode judge:** instead of primary/secondary taxonomy, ask the judge to select *all* applicable failure modes from the taxonomy for a given trace
- **Gold trajectories from notes:** prompt a frontier model with OSWorld-Human step notes to complete tasks and generate 100%-success gold traces; use these in lieu of human trajectories where full recordings are absent
- **Image diffusion for grounding markup:** use a model like Stable Diffusion 3 to annotate screenshots with unusual visual markers (e.g. houndstooth pattern) to aid click-target identification; detect markers via traditional CV
- **Streaming visual observation:** compressed memory / frame-diff summaries instead of full screenshot history in Transformer context — relevant for scrolling, video watching, dynamic UIs
- **Two-model architecture:** separate perception model (grounding/bounding boxes) from planning model; optionally add a third model for tool calls / documentation lookup
- **RL over predicted next-state:** train model to predict post-action state and use that to select best action; supervise reasoning traces
- **Memory compression for CUA:** represent GUI state as a learned latent rather than raw screenshots to handle pop-ups, ads, and sudden UI changes
- **Instruction enhancement LLM:** have an LLM rewrite the original task instruction with broad directions and explicit success metrics before passing to the CUA
- **YouTube tutorial training data:** use *Learning from Online Videos at Inference Time* approach; Gemma 4 trained on video as a reference
- **Auto-research / Hermes agent:** spin up agents to monitor experiments, survey literature, and brainstorm (reference: Andrej Karpathy's auto-research concept)

---

## Ideas & research directions

- **Core research question:** How much do successful (gold) trajectories improve automated LLM-as-judge error analysis of a CUA? What properties of a trajectory set influence that improvement?
- **Ablation structure:** compare judge (with gold trajectories) vs. judge (without gold trajectories) vs. human annotators; compute pairwise inter-annotator agreement
- **Failure taxonomy refinement:** consider prioritizing failure modes by (a) step of first occurrence, (b) downstream cascade impact, or (c) a custom prioritization function
- **Efficient thinking reward:** reward CUAs for reaching correct outcomes with fewer reasoning steps — addresses observed bloat in planning/reflection phases
- **Pixel-only small VLM agent:** central hypothesis that small models can become capable through better training, harness design, and memory rather than scaling alone
- **Fully open-source CUA differentiation:** use Molmo-style fully open models (known training provenance) vs. opaque open-weight models (QwenVL) to study how backbone properties affect CUA performance

---

## Action items

- [ ] @Raghav — Finish gathering screenshots of OSWorld-Human trajectories and merge into repo; start with pilot trajectories at `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- [ ] @Raghav — Investigate method to transform human OSWorld-Human notes into more accurate step-by-step instructions that raise human-agent success rate
- [ ] @Raghav — Debug OSWorld initialization bugs causing hanging states (e.g. Chrome not opening on setup)
- [ ] @Raghav — Manually annotate a set of ~10 selected traces for inter-annotator agreement study
- [ ] @Abdoul — Improve judge calibration on gold labels for 5 tasks meeting criteria: human agent succeeded, OpenCUA 7B and 3B both failed, judge produced failure-mode conclusions
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in each trace
- [ ] @Abdoul — Read related benchmarks beyond OSWorld to assess whether existing error analysis would undermine novelty of this approach
- [ ] @Abdoul — Manually annotate the same ~10 traces as Raghav for inter-annotator agreement comparison
- [ ] @Matt — Provide OpenAI API access to team
- [ ] @Amaad — For each Tier 1 benchmark, determine exactly what exists in the human trajectory data (real browser actions vs. notes vs. Playwright traces)
- [ ] @Amaad — Determine extent to which modern CUA work still relies on each candidate benchmark
- [ ] **Team** — Update OSWorld evaluation script to surface per-trace success/failure information visible to both human reviewers and the judge (include task JSON + evaluator function definitions)
- [ ] **Team** — Build "Oracle Agent" in OpenCUA to replay OSWorld-Human actions and generate a screenshot per step
- [ ] **Team** — Consolidate HTML annotation viewer features (Raghav's + Abdoul's); see viewer feature checklist in decisions
- [ ] **Team** — After full trajectory run, have an agent estimate frontier-model error-analysis cost from token counts before committing to full run

---

## Open questions

- Does using OSWorld-Human notes to prompt a frontier model actually yield near-100% success rates for gold trace generation? If not, why not?
- Is original OSWorld (v1) still a relevant evaluation target now that frontier labs benchmark on OSWorld v2.0?
- Is this research primarily relevant only to small models, given that frontier models have very low error rates on current benchmarks?
- Has anyone already answered the core research question (gold vs. no-gold trajectories in LLM-as-judge error analysis)?
- Should the failure-mode taxonomy prioritize errors by step of occurrence, downstream cascade impact, or a custom function?
- For the A3 benchmark, are the full ~300 human trajectories available as a standalone downloadable archive?
- For ClawBench, can the human reference runs be bulk-downloaded conveniently?
- What is the lab-standard setup on Bridges-2 for running vLLM with OpenCUA (conda env name, CUDA module, vLLM version)?
- Do small VLMs exhibit qualitatively different failure modes than large VLMs, and if so, can those failures be fixed via harness or training changes?
- Is there value in allowing a pixel-only GUI agent to use code for perception subtasks (cropping, frame-diff, structured memory)?
