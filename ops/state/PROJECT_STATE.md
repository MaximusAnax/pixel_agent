# Project state (living document)

> Auto-synthesized on 2026-07-10 by `ops/synthesize_state.py` (extractive mode). The compact digest also lives in `AGENTS.md` so Hermes loads it every turn. Edit upstream sources (meeting notes in `ops/meetings/`, weekly reports in `ops/reports/`), not this file — it is regenerated.

## Current snapshot

- **As of:** 2026-07-10
- **Most recent meeting:** 2026-07-10
- **Meetings folded in:** 2026-06-24, 2026-07-10

## Recent progress (from the latest weekly report)

From **2026-W26.md** (Executive summary):
- **Pipeline foundation shipped:** Both foundational PRs merged this week — Babel HF orchestration with Hermes setup (PR #1) and automated project-state context for Hermes (PR #2) — establishing the full remote analysis workflow end-to-end.
- **Pilot labeling underway:** The `opencua_a3b_pilot30` experiment group covers 361 inventoried episodes; 16 have been labeled by the Claude Sonnet 4.6 judge and are queued for human review at a cost of $0.26.
- **Adapter coverage complete:** Zero adapter gaps on the OpenCUA A3B package, a step forward from the 1-gap state reported in the prior week's run.
- **Provisional failure signal emerging:** Reasoning Drift and Goal Hallucination together account for 75 % of the 16 labeled episodes — early signal pending gold-set calibration.
- **Scale gap remains the key blocker:** 16 of 361 episodes labeled (4.4 %); throughput scaling is the immediate next milestone before results can be considered representative.
---

## Decisions (cumulative)

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

- Abdoul hit two environment issues on Bridges: CUDA 12.6 vs. vLLM expecting CUDA 13, and pip falling back to source tarball for vLLM 0.12.0 — resolved with vLLM 0.11.0  _( 2026-06-24 )_
- Historical screenshots can confuse models even when action history is included; unclear whether CUAs actually perform worse with screenshot context and why  _( 2026-06-24 )_
- Planning/reflection phases often take many more steps than necessary on medium/hard tasks  _( 2026-06-24 )_
- Icon accuracy is the main differentiator across grounding benchmarks (21–72% range); text grounding is relatively saturated (70–82%)  _( 2026-06-24 )_
- Post-training small models may be difficult since they are likely distillation-trained  _( 2026-06-24 )_
- Lots of benchmark/dataset storage blows up quickly due to image intensity — Babel storage should be adequate  _( 2026-06-24 )_

## Ideas on the table

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

- **Streaming visual observations** — compressed memory, frame-difference summaries, or learned temporal representations instead of full screenshot history in context; relevant for scrolling, video watching, game playing, dynamic UIs  _( 2026-06-24 )_
- **Harness design as a research variable** — iterating observe-plan-act loop, memory, retries, action abstraction, subgoals, self-checking; analogous to NAS  _( 2026-06-24 )_
- **Pixel-only CUA with optional code/tool use** — CodeAct-style tool use to compensate for small model capacity (image cropping, change tracking, structured memory)  _( 2026-06-24 )_
- **Fully open-source CUA** — use Molmo-class models (fully open weights + training provenance) to differentiate from QwenVL black-box baselines; enables studying how backbone VLM properties affect CUA performance  _( 2026-06-24 )_
- **RL training for small VLM agents** — after establishing imitation-learning baseline  _( 2026-06-24 )_
- **"Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding"** — paper discussed; use diffusion model to generate grounding labels; traditional CV as fallback for detecting markers  _( 2026-06-24 )_
