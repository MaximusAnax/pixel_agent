# Project state (living document)

> Auto-synthesized on 2026-08-10 by `ops/synthesize_state.py` (extractive mode). The compact digest also lives in `AGENTS.md` so Hermes loads it every turn. Edit upstream sources (meeting notes in `ops/meetings/`, weekly reports in `ops/reports/`), not this file — it is regenerated.

## Current snapshot

- **As of:** 2026-08-10
- **Most recent meeting:** 2026-08-07
- **Meetings folded in:** 2026-06-24, 2026-07-10, 2026-08-07

## Recent progress (from the latest weekly report)

From **2026-W32.md** (At a glance):
- **Merged PRs:** 0
- **Commits:** 1
- **Lines changed:** +34 / -0 across 1 files
- **New experiment runs:** 0

## Decisions (cumulative)

- Use **vLLM 0.11.0** as the lab-standard version on Bridges (resolves CUDA library mismatch)  _( 2026-08-07 )_
- Keep OSWorld VMs and inference both on Babel/Bridges (not split with AWS)  _( 2026-08-07 )_
- Judge pipeline: use a VLM judge given the reference trajectory, predicted trajectory, OSWorld metric (0–1), and evaluator test output to classify failure modes  _( 2026-08-07 )_
- CUA agent: Qwen3.5-VL 0.8B; Judge: Qwen3.5-VL 9B on Babel L40S GPUs  _( 2026-08-07 )_
- Cost threshold: if frontier-model error analysis costs ≤ $25, proceed without checking in with Matt; if more, check in first  _( 2026-08-07 )_
- Website updated combining Abdoul's and Raghav's trajectory viewers  _( 2026-08-07 )_
- Ran OSWorld with OSWorld-Human dataset as guide using UiTars-72B → **60/361 tasks succeeded**  _( 2026-08-07 )_
- **Current milestone = annotation-ready infrastructure** — OSWorld task/eval context, Human Agent screenshots for annotators + multimodal judge, mockup-approved dual-trace UI, provisional rejudge `osworld_v1` — not judge calibration or publication prevalence  _( 2026-07-10 )_
- **Provisional judge vs human gold** — versioned judge labels (`judge_context_version`) are reference only; `annotations.json` from abdoul/raghav is gold-in-progress  _( 2026-07-10 )_
- **Human reference is non-binding** — full human sequence (text + screenshots) for context; do not overfit; no forced step alignment to agent path  _( 2026-07-10 )_
- **Rejudge waits for Human Agent** — multimodal `osworld_v1` only after `oracle_status` ready/partial  _( 2026-07-10 )_
- **Grounding freeze** — after Abdoul sign-off, files in `errorAnalysis/docs/GROUNDING_MANIFEST.md` must not be edited without a new approved plan  _( 2026-07-10 )_
- **UI mockup before production** — static HTML mockups approved before Jinja/packet implementation  _( 2026-07-10 )_
- **Run everything on Babel/Bridges** — OSWorld VMs and inference stay on cluster, not local/AWS  _( 2026-06-24 )_
- **vLLM version standard on Bridges**: use **vLLM 0.11.0**, Python 3.11 conda env, `module load cuda/12.6.1`  _( 2026-06-24 )_
- **Cost threshold for frontier-model error analysis**: if estimated cost ≤ $25, proceed without checking with Matt; if more, check in first  _( 2026-06-24 )_
- **Error analysis model pair**: CUA = Qwen3.5-VL 0.8B, Judge = Qwen3.5-VL 9B (use different models for agent and judge)  _( 2026-06-24 )_
- **Start from existing HuggingFace trajectories** before generating new ones  _( 2026-06-24 )_
- **Focus models for trajectory review**: OpenCUA, Kimi, Sonnet 4.5 — not older models  _( 2026-06-24 )_
- **VLM-as-Judge approach**: provide reference trajectory, predicted trajectory, OSWorld metric score, and test outputs; ask VLM to classify error per taxonomy  _( 2026-06-24 )_

## Open feedback & critiques

- **OSWorld-Human incomplete steps** cause failures: e.g., instructions say to type in a search bar but never say to press Enter  _( 2026-08-07 )_
- **Model races ahead** while screen is still loading from the previous action  _( 2026-08-07 )_
- **OSWorld initialization errors**: initial environment not loaded properly (e.g., Chrome not opened on setup)  _( 2026-08-07 )_
- Benchmark drift concern: websites/software drift over time, invalidating trajectories  _( 2026-08-07 )_
- Relevance concern: frontier models evaluated on OSWorld v2.0 — is the benchmark still meaningful for small models?  _( 2026-08-07 )_
- Abdoul hit two environment issues on Bridges: CUDA 12.6 vs. vLLM expecting CUDA 13, and pip falling back to source tarball for vLLM 0.12.0 — resolved with vLLM 0.11.0  _( 2026-06-24 )_
- Historical screenshots can confuse models even when action history is included; unclear whether CUAs actually perform worse with screenshot context and why  _( 2026-06-24 )_
- Planning/reflection phases often take many more steps than necessary on medium/hard tasks  _( 2026-06-24 )_
- Icon accuracy is the main differentiator across grounding benchmarks (21–72% range); text grounding is relatively saturated (70–82%)  _( 2026-06-24 )_
- Post-training small models may be difficult since they are likely distillation-trained  _( 2026-06-24 )_
- Lots of benchmark/dataset storage blows up quickly due to image intensity — Babel storage should be adequate  _( 2026-06-24 )_

## Ideas on the table

- Give the Judge both agent and human trajectory; ask it to select **all applicable failure modes** (rather than primary/secondary classification only)  _( 2026-08-07 )_
- "Oracle Agent" that replays human actions in OpenCUA to generate a screenshot for every human step  _( 2026-08-07 )_
- Run OSWorld with a frontier model that reads OSWorld-Human notes → check if it achieves ~100%; diagnose why not  _( 2026-08-07 )_
- Generate grounding labels with an image diffusion model (Stable Diffusion 3); detect generated marker via traditional CV or a highly unusual synthetic pattern (e.g., houndstooth)  _( 2026-08-07 )_
- World models for planning in CUA; allow world model to explore new software and self-generate training data  _( 2026-08-07 )_
- Screenshot generation as a grounding method  _( 2026-08-07 )_
- Use YouTube computer-use tutorial videos as training data (cf. Gemma 4 video training)  _( 2026-08-07 )_
- Reward **efficient** thinking traces to reduce unnecessary planning steps  _( 2026-08-07 )_
- Compress GUI state history into a learned representation rather than raw screenshots, to handle pop-ups/ads and long-horizon context  _( 2026-08-07 )_
- Separate perception from planning: one model for candidate element selection, another for action output (potentially a third for tool calls / web search)  _( 2026-08-07 )_
- RL to teach best action by predicting post-action state; supervise reasoning traces  _( 2026-08-07 )_
- Special "call another model" action: main VLM acts, specialist VLM grounds/creates bounding boxes on demand  _( 2026-08-07 )_
- LLM instruction enhancer: expand original task instruction with broad directions and success metrics before agent execution  _( 2026-08-07 )_
- Agentic trajectory scraping from videos + synthetic augmentation to create new traces  _( 2026-08-07 )_
- Synthetic RL environment task generation  _( 2026-08-07 )_
- Auto-research setup (Karpathy-style): agents spin up to explore literature and brainstorm (P3 / later)  _( 2026-08-07 )_
- **VLM-as-Judge error taxonomy** — classify failures as perception/grounding vs. cognitive/planning errors  _( 2026-06-24 )_
- **World models for planning in CUA** — allow world model to explore new software and generate its own training data  _( 2026-06-24 )_
- **Screenshot generation as grounding method** — generate grounding labels with image diffusion (SD3); use an unusual visual marker (e.g., houndstooth pattern) that is easy for diffusion models to generate but doesn't appear in standard UIs  _( 2026-06-24 )_
- **GUI-state memory compression** — compress GUI state rather than passing raw screenshots; helps with sudden ads/pop-ups  _( 2026-06-24 )_
- **Two-model separation of perception and planning** — one model for candidate selection, one for action output; optional third model for tool calls (e.g., web search / documentation lookup)  _( 2026-06-24 )_
- **RL for best-action prediction** — model predicts state after candidate actions, is nudged toward best action; supervise reasoning traces  _( 2026-06-24 )_
- **Special "call-another-model" action** — main VLM delegates bounding-box/grounding reasoning to a specialized model  _( 2026-06-24 )_
- **Instruction enhancement via LLM** — LLM takes original task instruction and adds broad directions + success metrics before passing to CUA  _( 2026-06-24 )_
- **Reward efficient thinking** — incentivize shorter, more effective reasoning traces  _( 2026-06-24 )_
- **Training on YouTube computer-use tutorials** — leverage video demonstrations (CUA-Suite already exists; also online video inference paper)  _( 2026-06-24 )_
- **Agentic trajectory scraping from videos + synthetic augmentation** — create new traces from video; question: are models good enough to model computer environments?  _( 2026-06-24 )_
- **Synthetic RL environment task generation**  _( 2026-06-24 )_
- **Orthogonal icon-meaning data sources** — PowerPoint documentation, webpage alt-text, etc. to improve icon understanding  _( 2026-06-24 )_
- **Adaptive test-time compute for small models** — e.g., ReVL recursive grounding approach  _( 2026-06-24 )_
- **Auto-research agents** — spin up agents to survey literature and brainstorm (Karpathy-style); P3/later priority  _( 2026-06-24 )_

## Action items

- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: HumanAgent succeeded, OpenCUA-3B and 7B both failed, and Judge produced a failure-mode conclusion  _( 2026-08-07 )_
- [ ] @Abdoul — Read the space of other benchmarks (besides OSWorld) and determine whether existing error analysis would make our error analysis non-novel  _( 2026-08-07 )_
- [ ] @Abdoul — Write up Babel quick-start guide (GPU queues, env setup on remote machine)  _( 2026-08-07 )_
- [ ] @Abdoul — Make an SSH key for Babel/Bridges that the Hermes agent can use  _( 2026-08-07 )_
- [ ] @Abdoul — Set up cron jobs to monitor experiments  _( 2026-08-07 )_
- [ ] @Abdoul — Run failure analysis using pre-made prompt  _( 2026-08-07 )_
- [ ] @Raghav — Dive deeper into the Human Agent; find a method to transform human trajectories into more accurate instructions that raise Human Agent success rate  _( 2026-08-07 )_
- [ ] @Raghav — Investigate initialization bugs / OSWorld hanging states (e.g., why Chrome is not opened on setup)  _( 2026-08-07 )_
- [ ] @Raghav — Manually annotate the agreed-upon set of ~10 traces (one OpenCUA model)  _( 2026-08-07 )_
- [ ] @Abdoul — Manually annotate the same set of ~10 traces; compare with Raghav and Judge for inter-annotator agreement  _( 2026-08-07 )_
- [ ] @Abdoul — Aim for first full run of OpenCUA on Babel  _( 2026-08-07 )_
- [ ] @Amaad — Set up Hermes Agent; create `Skill.md` for onboarding a new idea, including instructions for accessing/updating meeting docs via Google Workspace CLI; share with team  _( 2026-08-07 )_
- [ ] @Amaad — After trajectories are collected, ask an agent to estimate frontier-model error-analysis cost (input/output tokens); proceed if ≤ $25, check with Matt if more  _( 2026-08-07 )_
- [ ] @Abdoul — Sign off Phase 0 / `GROUNDING_MANIFEST.md`  _( 2026-07-10 )_
- [ ] @Abdoul — After sign-off, start post–Phase 0 plan (vendor metadata → mockups → Human Agent → `osworld_v1`)  _( 2026-07-10 )_
- [ ] @Abdoul / @raghav — Discovery labeling on annotation-ready pilot packet (after infrastructure)  _( 2026-07-10 )_
- [ ] @Abdoul — Aim for first full run of OpenCUA on Babel  _( 2026-06-24 )_
- [ ] @Abdoul — Run failure analysis on OSWorld using pre-made prompt; use HuggingFace pre-generated trajectories first  _( 2026-06-24 )_
- [ ] @Abdoul — After collecting trajectories, have an agent compute token-cost estimate for frontier-model error analysis (proceed if ≤ $25; check with Matt if more)  _( 2026-06-24 )_
- [ ] @Abdoul — Document lab-standard Bridges env (conda env name, CUDA module, vLLM version) and share with team  _( 2026-06-24 )_
- [ ] @Abdoul — Set up SSH key for Babel/Bridges that the Hermes agent can use  _( 2026-06-24 )_
- [ ] @Abdoul — Write up 3 paper ideas  _( 2026-06-24 )_
- [ ] @Raghav — Continue literature review on CUA failure modes; summarize prior error analyses  _( 2026-06-24 )_
- [ ] @Raghav — Write up 3 paper ideas  _( 2026-06-24 )_
- [ ] @Amaad — Write up 3 paper ideas (noted: agentic trajectory scraping + synthetic augmentation; synthetic RL task generation)  _( 2026-06-24 )_
- [ ] @Abdoul — Set up Hermes Agent (P0)  _( 2026-06-24 )_
- [ ] @Abdoul — Create `Skill.md` for ramping up on new ideas; include instructions for accessing/updating meeting docs via Google Workspace CLI; share with team  _( 2026-06-24 )_
- [ ] @Abdoul — Set up cron jobs to monitor experiments  _( 2026-06-24 )_
- [ ] @Abdoul — SURA re-application (previous one did not go through)  _( 2026-06-24 )_

## Open questions

- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for running OpenCUA on Bridges?  _( 2026-08-07 )_
- Should OSWorld VMs run locally/AWS while inference stays on Bridges/Babel? *(Decided: keep everything on Bridges/Babel — but worth confirming)*  _( 2026-08-07 )_
- Is OSWorld still a relevant benchmark now that frontier models are evaluated on v2.0? Is error analysis only valuable for small models?  _( 2026-08-07 )_
- If we run OSWorld with a frontier model that sees the OSWorld-Human notes, do we get ~100% success? If not, why not?  _( 2026-08-07 )_
- What is the SOTA for small models on GUI grounding and on pixel-based computer use?  _( 2026-08-07 )_
- How do we definitively distinguish perception/grounding errors from cognitive/planning errors in automated analysis?  _( 2026-08-07 )_
- What counts as "small" for this project — 0.8B? 3B? 7B? 9B?  _( 2026-08-07 )_
- Do we care about open-weights (QwenVL) vs. fully open-source (Molmo) distinction, and should that differentiate the work?  _( 2026-08-07 )_
- None blocking Phase 0 freeze; taxonomy leaf additions deferred unless Abdoul requests  _( 2026-07-10 )_
- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for Bridges?  _( 2026-06-24 )_
- Should OSWorld VMs and inference always stay on Babel/Bridges? *(Decided: yes)*  _( 2026-06-24 )_
- Do CUAs perform worse when given screenshot context? If so, why?  _( 2026-06-24 )_
- Are existing models trained to understand sequences of video frames (video understanding), or just single frames?  _( 2026-06-24 )_
- What is SOTA for small models (≤ 3B) on GUI grounding benchmarks?  _( 2026-06-24 )_
- What is SOTA for small models on pixel-based computer use?  _( 2026-06-24 )_
- What counts as "small" for this project — 1B, 2B, 4B, 7B?  _( 2026-06-24 )_
- Do we prioritize open-weights (Qwen) vs. fully open-source (Molmo) models?  _( 2026-06-24 )_
- For streaming observations: beyond scrolling, what other CUA scenarios genuinely require temporal context?  _( 2026-06-24 )_
- Is there value in allowing a pixel-only GUI agent to use code (CodeAct-style)? What are the concrete use cases?  _( 2026-06-24 )_
- Is ScreenSpot or OSWorld-G the better starting benchmark for grounding experiments?  _( 2026-06-24 )_

## Technologies & tools discussed

- **Models:** UiTars-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B, Qwen3.5-VL 9B, Sonnet 4.6 (Judge)  _( 2026-08-07 )_
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, ScreenSpot, TheAgentCompany, WebArena  _( 2026-08-07 )_
- **Compute:** Babel (L40S GPUs), PSC Bridges-2 (GPU-shared, node v016), Slurm  _( 2026-08-07 )_
- **Infra:** vLLM 0.11.0 (resolved CUDA 12.6 vs. 13 incompatibility on Bridges), OpenCUA ([github.com/xlang-ai/OpenCUA](https://github.com/xlang-ai/OpenCUA))  _( 2026-08-07 )_
- **Papers referenced:**  _( 2026-08-07 )_
- OSWorld-Human: [arxiv.org/pdf/2506.16042](https://arxiv.org/pdf/2506.16042)  _( 2026-08-07 )_
- Error analysis draft: [arxiv.org/pdf/2606.31270](https://arxiv.org/pdf/2606.31270)  _( 2026-08-07 )_
- TheAgentCompany: [arxiv.org/pdf/2412.14161](https://arxiv.org/pdf/2412.14161)  _( 2026-08-07 )_
- AI/Human Workflow Comparison: [arxiv.org/abs/2510.22780v2](https://arxiv.org/abs/2510.22780v2)  _( 2026-08-07 )_
- OSWorld-G: [arxiv.org/pdf/2505.13227](https://arxiv.org/pdf/2505.13227)  _( 2026-08-07 )_
- GUI-Perturbed: [arxiv.org/pdf/2604.14262](https://arxiv.org/pdf/2604.14262)  _( 2026-08-07 )_
- CUA-Suite (video demos): [arxiv.org/abs/2603.24440](https://arxiv.org/abs/2603.24440)  _( 2026-08-07 )_
- Stable Diffusion 3: [arxiv.org/pdf/2403.03206](https://arxiv.org/pdf/2403.03206)  _( 2026-08-07 )_
- Qwen3-VL Technical Report: [arxiv.org/pdf/2511.21631](https://arxiv.org/pdf/2511.21631)  _( 2026-08-07 )_
- **Pixel Agent repo:** [github.com/MaximusAnax/pixel_agent](https://github.com/MaximusAnax/pixel_agent)  _( 2026-08-07 )_
- **OpenCUA** — https://github.com/xlang-ai/OpenCUA  _( 2026-06-24 )_
- **vLLM** — serving OpenCUA-7B; resolved CUDA mismatch by using vLLM 0.11.0 on PSC Bridges-2  _( 2026-06-24 )_
- **OSWorld / OSWorld-G** — https://arxiv.org/pdf/2505.13227  _( 2026-06-24 )_
- **ScreenSpot** — grounding benchmark  _( 2026-06-24 )_
- **Babel** (L40S GPUs) & **PSC Bridges-2** (cis260099p, GPU-shared) — compute clusters  _( 2026-06-24 )_
- **Slurm** — job scheduling  _( 2026-06-24 )_
- **Qwen3.5-VL 0.8B** (CUA) and **Qwen3.5-VL 9B** (judge) — model pair for failure analysis  _( 2026-06-24 )_
- **Stable Diffusion 3** — https://arxiv.org/pdf/2403.03206 (context: GUI grounding labels via diffusion)  _( 2026-06-24 )_
- **GUI-Perturbed** — https://arxiv.org/pdf/2604.14262  _( 2026-06-24 )_
- **Uground** — spatial reasoning for grounding  _( 2026-06-24 )_
- **OSWORLD-G** — https://arxiv.org/pdf/2505.13227  _( 2026-06-24 )_
- **CUA-Suite** — video demonstration dataset (arXiv: 2603.24440)  _( 2026-06-24 )_
- **Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs** — noted by Abdoul  _( 2026-06-24 )_
- **Video Understanding with Large Language Models: A Survey**  _( 2026-06-24 )_
- **Learning from Online Videos at Inference Time for Computer Use Agents**  _( 2026-06-24 )_
- **Qwen3-VL Technical Report** — https://arxiv.org/pdf/2511.21631  _( 2026-06-24 )_
- **Mac sleep commands** — `sudo pmset disablesleep 1/0`  _( 2026-06-24 )_

## Research directions

- **OSWorld error analysis** — primary near-term focus; identify perception/grounding errors vs. cognitive/planning errors  _( 2026-08-07 )_
- **Release proper OSWorld-Human dataset** with full trajectories (blocked by benchmark drift concern)  _( 2026-08-07 )_
- **Better CUA — generation-based** (e.g., diffusion grounding)  _( 2026-08-07 )_
- **Better CUA — small model** (pixel-only, laptop/edge-scale)  _( 2026-08-07 )_
- **Inter-annotator agreement study**: Abdoul vs. Raghav vs. Judge (Sonnet 4.6) on 10 manually selected traces; compute human–human and human–judge agreement  _( 2026-08-07 )_
- **Process Reward Models** (step-level verification): OSWorld-Verified + "Let's verify step by step"  _( 2026-08-07 )_
- **Adaptive test-time compute** for small models (e.g., ReVL recursive grounding approach)  _( 2026-08-07 )_
- **Fully open-source CUA**: differentiate from Qwen-based work by using fully open-provenance backbone (e.g., Molmo)  _( 2026-08-07 )_
- **Other benchmarks** to check for existing error analysis: TheAgentCompany, WebArena (may have human trajectories), OSWorld-G  _( 2026-08-07 )_
- **Streaming visual observations** — compressed memory, frame-difference summaries, or learned temporal representations instead of full screenshot history in context; relevant for scrolling, video watching, game playing, dynamic UIs  _( 2026-06-24 )_
- **Harness design as a research variable** — iterating observe-plan-act loop, memory, retries, action abstraction, subgoals, self-checking; analogous to NAS  _( 2026-06-24 )_
- **Pixel-only CUA with optional code/tool use** — CodeAct-style tool use to compensate for small model capacity (image cropping, change tracking, structured memory)  _( 2026-06-24 )_
- **Fully open-source CUA** — use Molmo-class models (fully open weights + training provenance) to differentiate from QwenVL black-box baselines; enables studying how backbone VLM properties affect CUA performance  _( 2026-06-24 )_
- **RL training for small VLM agents** — after establishing imitation-learning baseline  _( 2026-06-24 )_
- **"Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding"** — paper discussed; use diffusion model to generate grounding labels; traditional CV as fallback for detecting markers  _( 2026-06-24 )_
