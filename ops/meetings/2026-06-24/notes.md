# Meeting notes — 2026-06-24

## Attendees
- Abdoul
- Raghav
- Amaad

---

## Technologies discussed
- **OpenCUA** — https://github.com/xlang-ai/OpenCUA
- **vLLM** — serving OpenCUA-7B; resolved CUDA mismatch by using vLLM 0.11.0 on PSC Bridges-2
- **OSWorld / OSWorld-G** — https://arxiv.org/pdf/2505.13227
- **ScreenSpot** — grounding benchmark
- **Babel** (L40S GPUs) & **PSC Bridges-2** (cis260099p, GPU-shared) — compute clusters
- **Slurm** — job scheduling
- **Qwen3.5-VL 0.8B** (CUA) and **Qwen3.5-VL 9B** (judge) — model pair for failure analysis
- **Stable Diffusion 3** — https://arxiv.org/pdf/2403.03206 (context: GUI grounding labels via diffusion)
- **GUI-Perturbed** — https://arxiv.org/pdf/2604.14262
- **Uground** — spatial reasoning for grounding
- **OSWORLD-G** — https://arxiv.org/pdf/2505.13227
- **CUA-Suite** — video demonstration dataset (arXiv: 2603.24440)
- **Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs** — noted by Abdoul
- **Video Understanding with Large Language Models: A Survey**
- **Learning from Online Videos at Inference Time for Computer Use Agents**
- **Qwen3-VL Technical Report** — https://arxiv.org/pdf/2511.21631
- **Mac sleep commands** — `sudo pmset disablesleep 1/0`

---

## Decisions made
- **Run everything on Babel/Bridges** — OSWorld VMs and inference stay on cluster, not local/AWS
- **vLLM version standard on Bridges**: use **vLLM 0.11.0**, Python 3.11 conda env, `module load cuda/12.6.1`
- **Cost threshold for frontier-model error analysis**: if estimated cost ≤ $25, proceed without checking with Matt; if more, check in first
- **Error analysis model pair**: CUA = Qwen3.5-VL 0.8B, Judge = Qwen3.5-VL 9B (use different models for agent and judge)
- **Start from existing HuggingFace trajectories** before generating new ones
- **Focus models for trajectory review**: OpenCUA, Kimi, Sonnet 4.5 — not older models
- **VLM-as-Judge approach**: provide reference trajectory, predicted trajectory, OSWorld metric score, and test outputs; ask VLM to classify error per taxonomy

---

## Feedback / critiques
- Abdoul hit two environment issues on Bridges: CUDA 12.6 vs. vLLM expecting CUDA 13, and pip falling back to source tarball for vLLM 0.12.0 — resolved with vLLM 0.11.0
- Historical screenshots can confuse models even when action history is included; unclear whether CUAs actually perform worse with screenshot context and why
- Planning/reflection phases often take many more steps than necessary on medium/hard tasks
- Icon accuracy is the main differentiator across grounding benchmarks (21–72% range); text grounding is relatively saturated (70–82%)
- Post-training small models may be difficult since they are likely distillation-trained
- Lots of benchmark/dataset storage blows up quickly due to image intensity — Babel storage should be adequate

---

## Ideas considered
- **VLM-as-Judge error taxonomy** — classify failures as perception/grounding vs. cognitive/planning errors
- **World models for planning in CUA** — allow world model to explore new software and generate its own training data
- **Screenshot generation as grounding method** — generate grounding labels with image diffusion (SD3); use an unusual visual marker (e.g., houndstooth pattern) that is easy for diffusion models to generate but doesn't appear in standard UIs
- **GUI-state memory compression** — compress GUI state rather than passing raw screenshots; helps with sudden ads/pop-ups
- **Two-model separation of perception and planning** — one model for candidate selection, one for action output; optional third model for tool calls (e.g., web search / documentation lookup)
- **RL for best-action prediction** — model predicts state after candidate actions, is nudged toward best action; supervise reasoning traces
- **Special "call-another-model" action** — main VLM delegates bounding-box/grounding reasoning to a specialized model
- **Instruction enhancement via LLM** — LLM takes original task instruction and adds broad directions + success metrics before passing to CUA
- **Reward efficient thinking** — incentivize shorter, more effective reasoning traces
- **Training on YouTube computer-use tutorials** — leverage video demonstrations (CUA-Suite already exists; also online video inference paper)
- **Agentic trajectory scraping from videos + synthetic augmentation** — create new traces from video; question: are models good enough to model computer environments?
- **Synthetic RL environment task generation**
- **Orthogonal icon-meaning data sources** — PowerPoint documentation, webpage alt-text, etc. to improve icon understanding
- **Adaptive test-time compute for small models** — e.g., ReVL recursive grounding approach
- **Auto-research agents** — spin up agents to survey literature and brainstorm (Karpathy-style); P3/later priority

---

## Ideas & research directions
- **Streaming visual observations** — compressed memory, frame-difference summaries, or learned temporal representations instead of full screenshot history in context; relevant for scrolling, video watching, game playing, dynamic UIs
- **Harness design as a research variable** — iterating observe-plan-act loop, memory, retries, action abstraction, subgoals, self-checking; analogous to NAS
- **Pixel-only CUA with optional code/tool use** — CodeAct-style tool use to compensate for small model capacity (image cropping, change tracking, structured memory)
- **Fully open-source CUA** — use Molmo-class models (fully open weights + training provenance) to differentiate from QwenVL black-box baselines; enables studying how backbone VLM properties affect CUA performance
- **RL training for small VLM agents** — after establishing imitation-learning baseline
- **"Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding"** — paper discussed; use diffusion model to generate grounding labels; traditional CV as fallback for detecting markers

---

## Action items
- [ ] @Abdoul — Aim for first full run of OpenCUA on Babel
- [ ] @Abdoul — Run failure analysis on OSWorld using pre-made prompt; use HuggingFace pre-generated trajectories first
- [ ] @Abdoul — After collecting trajectories, have an agent compute token-cost estimate for frontier-model error analysis (proceed if ≤ $25; check with Matt if more)
- [ ] @Abdoul — Document lab-standard Bridges env (conda env name, CUDA module, vLLM version) and share with team
- [ ] @Abdoul — Set up SSH key for Babel/Bridges that the Hermes agent can use
- [ ] @Abdoul — Write up 3 paper ideas
- [ ] @Raghav — Continue literature review on CUA failure modes; summarize prior error analyses
- [ ] @Raghav — Write up 3 paper ideas
- [ ] @Amaad — Write up 3 paper ideas (noted: agentic trajectory scraping + synthetic augmentation; synthetic RL task generation)
- [ ] @Abdoul — Set up Hermes Agent (P0)
- [ ] @Abdoul — Create `Skill.md` for ramping up on new ideas; include instructions for accessing/updating meeting docs via Google Workspace CLI; share with team
- [ ] @Abdoul — Set up cron jobs to monitor experiments
- [ ] @Abdoul — SURA re-application (previous one did not go through)

---

## Open questions
- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for Bridges?
- Should OSWorld VMs and inference always stay on Babel/Bridges? *(Decided: yes)*
- Do CUAs perform worse when given screenshot context? If so, why?
- Are existing models trained to understand sequences of video frames (video understanding), or just single frames?
- What is SOTA for small models (≤ 3B) on GUI grounding benchmarks?
- What is SOTA for small models on pixel-based computer use?
- What counts as "small" for this project — 1B, 2B, 4B, 7B?
- Do we prioritize open-weights (Qwen) vs. fully open-source (Molmo) models?
- For streaming observations: beyond scrolling, what other CUA scenarios genuinely require temporal context?
- Is there value in allowing a pixel-only GUI agent to use code (CodeAct-style)? What are the concrete use cases?
- Is ScreenSpot or OSWorld-G the better starting benchmark for grounding experiments?
