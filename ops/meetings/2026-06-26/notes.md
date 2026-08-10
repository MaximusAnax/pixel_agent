# Meeting notes — 2026-06-26

## Attendees
- Abdoul
- Raghav
- Amaad
- Matt (mentioned)

---

## Technologies discussed
- **OpenCUA** — https://github.com/xlang-ai/OpenCUA
- **pixelAgent repo** — https://github.com/MaximusAnax/pixel_agent
- **vLLM** — v0.11.0 confirmed working on PSC Bridges-2 (CUDA 12.6); v0.23 / v0.12.0 had compatibility issues
- **Compute clusters** — Babel (L40S GPUs, Andrew IDs), PSC Bridges-2 (`cis260099p`, GPU-shared), Slurm
- **Models** — OpenCUA-7B, Qwen3.5-VL 0.8B (CUA), Qwen3.5-VL 9B (judge), Kimi, Claude Sonnet 4.5
- **Benchmarks** — OSWorld, OSWorld-Verified, OSWorld-G (https://arxiv.org/pdf/2505.13227), ScreenSpot
- **Papers discussed:**
  - *Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding*
  - *Stable Diffusion 3* — https://arxiv.org/pdf/2403.03206
  - *Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs*
  - *CUA-Suite: Massive Human-annotated Video Demonstrations for Computer-Use Agents* — arXiv:2603.24440
  - *GUI-Perturbed* — https://arxiv.org/pdf/2604.14262
  - *Uground* (spatial reasoning / grounding)
  - *Video Understanding with Large Language Models: A Survey*
  - *Learning from Online Videos at Inference Time for Computer Use Agents*
  - *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*
  - *OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks*
  - *Qwen2-VL / Qwen3-VL Technical Reports* — https://arxiv.org/pdf/2511.21631
- **Mac sleep commands** — `sudo pmset disablesleep 1` / `0`

---

## Decisions made
- Run OSWorld VMs and inference **both on Babel/Bridges** (not locally or AWS)
- Use **vLLM 0.11.0** on Bridges (resolves CUDA 12.6 / libcudart incompatibility)
- Error analysis setup: CUA = Qwen3.5-VL 0.8B; Judge = Qwen3.5-VL 9B (different models for agent vs. judge)
- Cost threshold for frontier-model error analysis: **≤ $25 → proceed without asking Matt; > $25 → check in first**
- Use pre-existing HuggingFace trajectories first; generate own trajectories later
- Prioritize **OpenCUA** with vLLM serving for inference efficiency
- Focus relevant models on OpenCUA, Kimi, Sonnet 4.5 — not older models
- Use **Babel L40S GPUs** for judge inference

---

## Feedback / critiques
- Historical screenshots in context can **confuse models** even with action history included — unclear if providing screenshot context helps or hurts CUA performance
- Small models (e.g., 1B) likely distillation-trained, making post-training approaches harder to differentiate
- Planning/reflection phases often take **far more steps than required**, especially on hard tasks (10+ steps)
- Icon accuracy is the **main performance differentiator** (21–72% range); text grounding is relatively saturated (70–82%)
- Models are stateless across trajectories — a known failure mode in long-horizon tasks

---

## Ideas considered
- **World models for CUA planning** — allow world model to explore new software and self-generate training data
- **Screenshot generation as a grounding method** — generate grounding labels via image diffusion; use unusual patterns (e.g., houndstooth) easy for diffusion but absent from standard UIs; detect via traditional CV
- **Compressed GUI state as memory** — represent prior screen history as a learned state rather than raw screenshots; could handle sudden ads/pop-ups
- **Two-model architecture** — one model for candidate grounding/perception, one for action/planning; optionally a third for tool calls (web search, documentation lookup)
- **RL to predict post-action state** — supervise reasoning traces to steer model toward best action
- **Special "call another model" action** — main VLM delegates bounding-box reasoning to a specialized grounding model
- **Instruction enhancement via LLM** — expand original task instruction with broad directions and success metrics before passing to VLM
- **Reward efficient thinking** — incentivize shorter, more effective reasoning traces
- **Train on YouTube computer-use tutorials** — leverage video understanding (Gemma 4 trained on video)
- **Agentic trajectory scraping from videos + synthetic augmentation**
- **Synthetic RL environment task generation**
- **Adaptive test-time compute for small models** — e.g., ReVL recursive grounding approach
- **Orthogonal data sources for icon understanding** — PowerPoint documentation, webpage alt-text
- **Auto-research agent** (P3/later) — à la Andrej Karpathy's auto-research; spins up agents to survey literature and brainstorm

---

## Ideas & research directions
- **Streaming visual observation** — frame-difference summaries, compressed memory, learned temporal representations; relevant for scrolling, video watching, game play, dynamic UIs; not solved even for frontier models
- **Pixel-only GUI agent with code/tool use** — allow agent to crop images, track frame changes, maintain structured memory via code (CodeAct style); compensates for small model capacity
- **Harness design as NAS analog** — iterate observe–plan–act loop, memory, retries, action abstraction, subgoals; harness may matter as much as model weights for small VLMs
- **Fully open-source CUA** — use Molmo-style fully open models (known training provenance) vs. black-box open-weight models (Qwen), to isolate backbone VLM effects on downstream CUA performance
- **Process Reward Models for CUA** — *Let's Verify Step by Step* applied to OSWorld-Verified

---

## Action items
- [ ] @Abdoul — Complete first full run of OpenCUA on Babel
- [ ] @Abdoul — Run failure/error analysis using pre-made prompt on OSWorld trajectories (start with HuggingFace pre-generated trajectories)
- [ ] @Abdoul — After trajectories collected, ask agent to compute token cost estimate for frontier-model error analysis; proceed per $25 threshold
- [ ] @Abdoul — Write up Babel quick-start guide (GPU queues, env setup on remote machine)
- [ ] @Abdoul — Document lab-standard Bridges setup: conda env name, CUDA module (`cuda/12.6.1`), vLLM version (0.11.0)
- [ ] @Abdoul — Make an SSH key for Babel/Bridges that the Hermes agent can use
- [ ] @Abdoul — Set up Hermes Agent (P0); create `Skill.md` for ramping up on new ideas; add instructions for Google Workspace CLI access to meeting docs; share with team
- [ ] @Abdoul — Set up cron jobs to monitor experiments
- [ ] @Abdoul — Write up 3 paper ideas
- [ ] @Raghav — Write up 3 paper ideas
- [ ] @Amaad — Write up 3 paper ideas
- [ ] @Raghav — Continue literature review on CUA failure modes; focus on OSWorld-G and ScreenSpot
- [ ] @Raghav — Look more closely at model reasoning traces when analyzing trajectories
- [ ] @Amaad — Investigate novel dataset not in Qwen training data for grounding differentiation; explore synthetic data gen / data augmentation (paired screenshot + HTML)

---

## Open questions
- What is the lab-standard conda env name, CUDA module, and vLLM version/wheel for serving on Bridges?
- Should OSWorld VMs run locally/AWS while inference stays on Bridges/Babel? *(Decided: keep everything on Bridges/Babel — confirm this holds)*
- Do CUAs perform **worse** when given screenshot context? If so, why?
- Are current CUA models (e.g., Qwen) even trained to understand sequences of video frames?
- What is SOTA for **small models** (≤3B) on GUI grounding benchmarks?
- What is SOTA for **small models** on pixel-based computer use (OSWorld-Verified)?
- What counts as "small" for this project — 2B? 4B? 7B?
- Do we prioritize **open-weights** (Qwen) vs. **fully open-source** (Molmo) models, and does that distinction matter for our contribution?
- Is there existing error analysis in the literature we can build on directly?
