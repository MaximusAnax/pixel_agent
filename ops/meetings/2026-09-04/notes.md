# Meeting notes — 2026-09-04

## Attendees

- Raghav
- Abdoul
- Amaad
- Matt (referenced; not confirmed present)

---

## Technologies discussed

- **Models / agents:** OpenCUA-3B, OpenCUA-7B, UiTars-72B (grounding), Qwen3.5-VL 0.8B / 9B, Sonnet 4.6 (judge), frontier models (Opus 5)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, WebArena, VisualWebArena, ScreenSpot V2, ClawBench, A3 / AITK, OmniGUI, VideoCUA / CUA-Suite, WebChain, Mind2Web, WebLINX, AITW, UI-Vision, PC Agent-E, AndroidWorld, ScreenSpot Pro
- **Clusters:** Babel (L40S GPUs), PSC Bridges-2 (CUDA 12.6, vLLM 0.11.0 confirmed working)
- **Infrastructure:** vLLM, Slurm, conda (Python 3.11 env), OSWorld VM environments
- **Papers / datasets referenced:**
  - CUADebug `[2608.02643]`
  - OSWorld-Human `arxiv:2506.16042`
  - Error analysis paper `arxiv:2606.31270`
  - How benchmarks mis-score `arxiv:2607.28367`
  - Qwen3-VL technical report `arxiv:2511.21631`
  - GUI-Perturbed `arxiv:2604.14262`
  - OSWORLD-G `arxiv:2505.13227`
  - CUA-Suite / VideoCUA `arxiv:2603.24440`
  - ClawBench `arxiv:2604.08523`
  - A3 / AITK `arxiv:2501.01149`
  - WebChain `arxiv:2603.05295`
  - PC Agent-E `arxiv:2505.13909`
  - AITW `arxiv:2307.10088`
  - OmniGUI `arxiv:2605.18758`
  - UI-Vision `arxiv:2503.15661`
  - TheAgentCompany `arxiv:2412.14161`
  - Learning from Online Videos at Inference Time for CUAs
  - Beyond the Final Answer (tool-augmented agent reasoning trajectories)

---

## Decisions made

- **vLLM version fixed:** Use vLLM 0.11.0 on Bridges-2 with CUDA 12.6; earlier versions cause `libcudart.so.13` import errors.
- **Judge model:** Sonnet 4.6 (as of Monday meeting).
- **Agent models for traces:** OpenCUA-3B and OpenCUA-7B.
- **Grounding model:** UiTars-72B; achieved 60/361 tasks on OSWorld with OSWorld-Human as guide.
- **Keep compute on Bridges / Babel** rather than splitting OSWorld VMs to AWS.
- **Cost threshold for error analysis:** If frontier-model judge costs ~$25, proceed without asking Matt; if more, check in first.
- **Tier 1 benchmarks for human ↔ agent comparison:** OSWorld-Human, WebArena human trajectories, VisualWebArena human trajectories, ClawBench, A3.
- **NeurIPS concurrent-work policy noted:** Papers appearing after March 1 2025 (e.g. CUADebug) are considered concurrent; no comparison required.
- **Pilot annotation set:** `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`

---

## Feedback / critiques

- OSWorld-Human instructions are **incomplete** (e.g. instruct model to type in search bar but never press Enter), causing gold-label creation to fail.
- Model proceeds to the next action **while the screen is still loading** from the previous action.
- **OSWorld initialization errors** — initial environment sometimes not loaded properly (e.g. Chrome not opened on setup); leads to hanging states.
- CUADebug (`2608.02643`) is very similar to the team's planned approach (failure taxonomy + analysis); team's novelty must rest on use of human trajectories.
- Existing benchmark websites / software **drift over time**, making any released gold trajectory dataset potentially stale.
- Frontier models (Sonnet, etc.) are now evaluated on OSWorld v2.0 — raises question of whether OSWorld is still relevant for small-model error analysis.
- Historical screenshots in context can **confuse** models even when action history is provided; unclear whether current VLMs are trained to understand sequential frames.

---

## Ideas considered

- **Oracle Agent:** Run OSWorld with a frontier model that reads OSWorld-Human notes to generate gold trajectories; target 100% success rate; use these as substitutes when no real human trajectories exist.
- **Multiple failure-mode annotation:** Ask judge to select *all* applicable failure modes rather than primary/secondary only.
- **Failure prioritization function:** Weight failure modes by step of occurrence (earlier = higher impact), downstream cascade count, or a custom priority function.
- **Image-diffusion-based grounding markup:** Use Stable Diffusion 3 to add unusual visual markers (e.g. houndstooth pattern) on screenshots to aid grounding; find markers with traditional CV.
- **World models for CUA planning:** Allow world model to explore new software and self-generate training data.
- **Compressed GUI state / memory:** Encode GUI state as a learned representation rather than raw screenshots to handle long-horizon and pop-up/ad scenarios (Raghav).
- **Dual-model perception + planning split:** Separate grounding model (bounding boxes) from planning model; optionally a third model for web-search tool calls (Raghav).
- **RL with predicted state supervision:** Predict post-action state to guide action selection; supervise reasoning traces (Raghav).
- **Instruction enhancement via LLM:** Have an LLM rewrite the task instruction with broad directions and success metrics before the agent starts (Raghav).
- **Agentic trajectory scraping from YouTube tutorials:** Use video understanding to extract computer-use traces for training data (Amaad).
- **Synthetic RL environment task generation** (Amaad).
- **Alt-text / documentation as orthogonal grounding signal:** Use webpage alt-text or app documentation (e.g. PowerPoint docs) to improve icon understanding.
- **Adaptive test-time compute for small models:** E.g. ReVL recursive grounding approach.
- **Auto-research agent** (Andrej Karpathy–style): Spin up agents that survey literature and brainstorm on a problem (P3 / later).
- **Idea-generation prompting strategies:** Critique a specific paper, refine a specific idea with 10 variants, ask for 10 closest related papers to a proposed idea.

---

## Ideas & research directions

- **Core research question:** How much do successful (gold) human trajectories improve automated LLM-as-a-judge error analysis of a CUA? What properties of those trajectories drive the improvement?
- **Comparison baseline:** Paper *Beyond the Final Answer* shows error analysis without golden traces — establish this as the no-gold baseline.
- **Inter-annotator agreement study:** Raghav and Abdoul each manually annotate the same ~10 traces; compute agreement pairs: human₁/human₂, human₁/judge, human₂/judge, judge(with gold)/judge(without gold).
- **Efficient thinking reward:** Reward CUAs for *efficient* reasoning traces, not just correct answers, to reduce excess steps.
- **Video-frame understanding for CUAs:** Investigate whether current VLMs degrade with screenshot history; compare models trained on video sequences.
- **Pixel-only streaming observations:** Compressed memory / frame-difference summaries for scrolling, video-watching, and dynamic UI tasks — not yet solved for frontier models.
- **Fully open-source CUA baseline:** Use Molmo or similar fully open-source (not just open-weights) VLM to enable transparent training and differentiation from QwenVL black-box provenance.
- **Code-augmented pixel-only agent:** Allow GUI agent to call code for image cropping, frame differencing, structured memory, or visual preprocessing to compensate for small model capacity.

---

## Action items

- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset via benchmark environment; merge into repo.
- [ ] @Raghav — Investigate methods to transform OSWorld-Human step notes into more accurate instructions that increase Oracle/human-agent success rate.
- [ ] @Raghav — Diagnose OSWorld initialization bugs and hanging states (e.g., Chrome not opened on setup).
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: (1) human/Oracle agent succeeded, (2) OpenCUA-7B and -3B both failed, and (3) judge produced failure-mode conclusions.
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace.
- [ ] @Abdoul — Read further into failure analysis papers to survey existing failure categorization schemes.
- [ ] @Abdoul — Investigate broader related work; confirm whether any existing paper answers the gold-trajectory error-analysis research question.
- [ ] @Amaad — For each Tier 1 benchmark, document exactly what the human "trajectory" data contains (real actions vs. notes vs. Playwright traces, etc.).
- [ ] @Amaad — Verify that ClawBench and A3 human reference runs can be bulk-downloaded before committing to them.
- [ ] @Matt — Provide OpenAI API access to team.
- [ ] @Raghav / @Abdoul — Manually annotate the same pilot set of ~10 traces (one OpenCUA model); compute inter-annotator agreement with each other and with the judge.
- [ ] @Abdoul — Set up OSWorld evaluation script to output per-trace success/failure metadata visible to humans and passed to the judge (include task description JSON + evaluator metric functions from `desktop_env/evaluators/metrics`).
- [ ] @Abdoul — Make OSWorld-Human traces visible alongside OpenCUA traces in the annotation viewer.
- [ ] @Raghav — Build Oracle Agent within OpenCUA that replays human actions and generates a screenshot per step.
- [ ] @Abdoul / @Raghav — Consolidate HTML annotation tool features (see viewer feature list in notes); agree on canonical task order, canonical data format, and shared task IDs.
- [ ] @Amaad — Set up Hermes Agent; create `Skill.md` for new-idea ramp-up; add Google Workspace CLI instructions; share with team.
- [ ] @Amaad — Set up cron jobs to monitor experiments.
- [ ] @Amaad — Create SSH key for Babel/Bridges usable by the agent.
- [ ] @Abdoul — Complete Babel quick-start guide (GPU queues, env setup on remote machine); credentials were not yet created at last check-in.
- [ ] @Raghav / @Abdoul — After all trajectories are collected, ask an agent to estimate frontier-model judge cost (input/output tokens); proceed if ~$25, else check with Matt.

---

## Open questions

- Why is Chrome not opened during OSWorld environment setup (initialization bug)?
- Should OSWorld VMs run locally or on AWS while inference runs on Bridges/Babel, or keep everything on Bridges/Babel?
- What is the lab-standard conda env name, CUDA module, and vLLM version for serving OpenCUA on Bridges?
- Do modern CUA papers still rely on OSWorld, or has OSWorld v2.0 superseded it to the point where small-model error analysis is only marginally relevant?
- Is the benchmark still relevant if frontier models have very few errors on it?
- Has any existing paper already answered: "How much do gold trajectories improve automated CUA error analysis?"
- How do we reliably distinguish **perception/grounding errors** from **cognitive/planning errors** in the judge output?
- How should failure modes be prioritized — by step of occurrence, downstream cascade count, or a custom function?
- Should the updated taxonomy use a select-all failure-mode approach rather than primary/secondary?
- Do CUAs perform *worse* when given screenshot history as context, and if so, why?
- Are current VLMs trained to understand sequential video frames, or only isolated images?
- What is the SOTA for small models (≤7B) on GUI grounding benchmarks (ScreenSpot V2, OSWorld-G)?
- What is the SOTA for small models on pixel-only computer use (OSWorld-Verified, AndroidWorld)?
- Is the "fully open-source" (vs. open-weights) distinction a meaningful differentiator for this work?
