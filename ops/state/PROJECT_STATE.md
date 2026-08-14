# Project state

> Auto-synthesized on 2026-08-14 by `ops/synthesize_state.py` (extractive mode). The compact digest also lives in `AGENTS.md` so Hermes loads it every turn. Edit upstream sources (meeting notes in `ops/meetings/`, weekly reports in `ops/reports/`), not this file — it is regenerated.

## Current snapshot

- **As of:** 2026-08-14
- **Most recent meeting:** 2026-08-14
- **Meetings folded in:** 2026-06-24, 2026-07-10, 2026-08-07, 2026-08-14

## Recent progress (from the latest weekly report)

From **2026-W33.md** (At a glance):
- **Merged PRs:** 0
- **Commits:** 9
- **Lines changed:** +5,543 / −892 across 56 files
- **Experiment groups (deduped):** 0
- **All-applicable labeling migration shipped** (PXA-001/002/003/016): schema now allows multiple concurrent failure labels per episode; ratified in compendium
- **PXA-024 scoped**: frontier-model Human Agent ceiling run formally ticketed
- **Review loop closed** on PXA-021/022/023: Raghav handoff and research prompt documented
- **Oracle → handoff refactor** committed as WIP safety checkpoint; not yet merged
- **pixelAgent compendium formalised** — single authoritative reference for taxonomy, labeling rules, methodology decisions
- **No experiment data**: pipeline infrastructure and labeling foundations must stabilise before next run batch; all prior failure labels remain provisional pending PXA-024 gold-set calibration

## Decisions (cumulative)

- Use **UITARS-72B** as grounding model for OSWorld runs; current success rate: **60/361 tasks** _(2026-08-07/14)_
- Use **Sonnet 4.6** as LLM judge over OpenCUA-3B and OpenCUA-7B traces _(2026-08-14)_
- **OSWorld-Human not yet folded in** to the judge pipeline — adding it is the next priority _(2026-08-14)_
- Judge should receive: task description JSON **and** relevant evaluator metric functions (e.g., `is_expected_tabs` source from OSWorld evaluators repo) _(2026-08-14)_
- Error prioritization to be explored along three axes: step of occurrence, downstream impact, and a to-be-designed prioritization function _(2026-08-14)_
- **NeurIPS concurrent-work policy**: papers appearing after March 1 2025 (including CUADebug, arXiv:2608.02643) are considered concurrent; comparison not required _(2026-08-14)_
- **All-applicable labeling**: judge selects all applicable failure modes per episode rather than primary/secondary only _(2026-08-14, PXA-001/002/003/016)_
- Use **vLLM 0.11.0** as the lab-standard version on Bridges (CUDA 12.6 compatible; do not use vLLM 0.23 which requires CUDA 13) _(2026-08-07)_
- Keep OSWorld VMs and inference both on Babel/Bridges — not split with AWS _(2026-08-07)_
- CUA agent: **Qwen3.5-VL 0.8B**; Judge: **Qwen3.5-VL 9B** on Babel L40S GPUs _(2026-08-07)_
- Cost threshold: if frontier-model error analysis costs ≤ $25, proceed without checking in with Matt; if more, check in first _(2026-08-07)_
- **Current milestone = annotation-ready infrastructure** — OSWorld task/eval context, Human Agent screenshots for annotators + multimodal judge, mockup-approved dual-trace UI, provisional rejudge `osworld_v1` _(2026-07-10)_
- **Provisional judge vs human gold** — versioned judge labels (`judge_context_version`) are reference only; `annotations.json` is gold-in-progress _(2026-07-10)_
- **Human reference is non-binding** — full human sequence for context; no forced step alignment to agent path _(2026-07-10)_
- **Rejudge waits for Human Agent** — multimodal `osworld_v1` only after `oracle_status` ready/partial _(2026-07-10)_
- **Grounding freeze** — after Abdoul sign-off, files in `errorAnalysis/docs/GROUNDING_MANIFEST.md` must not be edited without a new approved plan _(2026-07-10)_
- **Start from existing HuggingFace trajectories** before generating new ones _(2026-06-24)_
- **Focus models for trajectory review**: OpenCUA, Kimi, Sonnet 4.5 — not older models _(2026-06-24)_

## Open feedback & critiques

- **OSWorld-Human incomplete steps** cause failures: e.g., instructions say to type in a search bar but never say to press Enter _(2026-08-07/14)_
- **Model races ahead** while screen is still loading from the previous action _(2026-08-07)_
- **OSWorld initialization errors**: initial environment not loaded properly (e.g., Chrome not opened on setup) _(2026-08-07)_
- **CUADebug** (arXiv:2608.02643) is very similar in scope — uses failure-mode taxonomy + automated analysis; our novelty relative to it is the use of human/gold trajectories _(2026-08-14)_
- Benchmark drift concern: websites/software drift over time, invalidating trajectories _(2026-08-07)_
- Relevance concern: frontier models evaluated on OSWorld v2.0 — is the benchmark still meaningful for small models? _(2026-08-07)_
- Historical screenshots can confuse models even when action history is included _(2026-06-24)_
- Planning/reflection phases often take many more steps than necessary on medium/hard tasks _(2026-06-24)_
- Icon accuracy is the main differentiator across grounding benchmarks (21–72% range); text grounding is relatively saturated (70–82%) _(2026-06-24)_
- Post-training small models may be difficult since they are likely distillation-trained _(2026-06-24)_

## Ideas on the table

- **Inter-annotator agreement study**: Raghav and Abdoul each independently annotate the same ~10-trace failure set; compute agreement across pairs: (human A / human B), (human A / judge), (human B / judge) _(2026-08-07/14)_
- **Gold trajectory generation via frontier model**: where only human notes exist (OSWorld-Human), prompt a frontier model with those notes during live task execution; target ~100% success rate as gold standard _(2026-08-14)_
- **Failure mode prioritization function**: weight by step of occurrence (earlier = higher importance) and downstream failure count as impact signal _(2026-08-14)_
- **"Oracle Agent"** that replays human actions in OpenCUA to generate a screenshot for every human step _(2026-08-07/14)_
- Give the Judge both agent and human trajectory; ask it to select **all applicable failure modes** _(2026-08-07)_
- Run OSWorld with a frontier model reading OSWorld-Human notes → check if it achieves ~100%; diagnose why not _(2026-08-07)_
- Generate grounding labels with an image diffusion model (Stable Diffusion 3); detect generated marker via traditional CV or a highly unusual synthetic pattern (e.g., houndstooth) _(2026-08-07)_
- World models for planning in CUA; allow world model to explore new software and self-generate training data _(2026-08-07)_
- Use YouTube computer-use tutorial videos as training data (cf. Gemma 4 video training; CUA-Suite) _(2026-08-07)_
- Reward **efficient** thinking traces to reduce unnecessary planning steps _(2026-08-07)_
- Compress GUI state history into a learned representation rather than raw screenshots, to handle pop-ups/ads and long-horizon context _(2026-08-07)_
- Separate perception from planning: one model for candidate element selection, another for action output (optionally a third for tool calls / web search) _(2026-08-07)_
- RL to teach best action by predicting post-action state; supervise reasoning traces _(2026-08-07)_
- Special "call another model" action: main VLM acts, specialist VLM grounds/creates bounding boxes on demand _(2026-08-07)_
- LLM instruction enhancer: expand original task instruction with broad directions and success metrics before agent execution _(2026-08-07)_
- Agentic trajectory scraping from videos + synthetic augmentation to create new traces _(2026-08-07)_
- Synthetic RL environment task generation _(2026-08-07)_
- **Process Reward Models** (step-level verification): OSWorld-Verified + "Let's verify step by step" _(2026-08-07)_
- **Adaptive test-time compute** for small models (e.g., ReVL recursive grounding approach) _(2026-08-07)_
- **Fully open-source CUA**: differentiate from Qwen-based work using fully open-provenance backbone (e.g., Molmo) _(2026-08-07)_
- **Orthogonal icon-meaning data sources** — PowerPoint documentation, webpage alt-text, etc. _(2026-06-24)_
- Auto-research agents — spin up agents to survey literature and brainstorm (Karpathy-style); P3/later _(2026-06-24)_
- Use AI idea-generation prompts strategically: ask model to critique a specific paper, refine a specific idea, or identify 10 most closely related papers to a given idea _(2026-08-14)_

## Action items

- [ ] @Abdoul — Improve judge calibration on 5 pilot tasks: human-agent succeeded, OpenCUA-3B and -7B both failed, judge produced a failure-mode conclusion _(2026-08-07/14)_
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace _(2026-08-14)_
- [ ] @Abdoul — Continue reading failure analysis papers for taxonomy categorization approaches (including CUADebug arXiv:2608.02643) _(2026-08-14)_
- [ ] @Abdoul — Read the space of other benchmarks (besides OSWorld) and determine whether existing error analysis would render our error analysis non-novel _(2026-08-07/14)_
- [ ] @Abdoul — Write up Babel quick-start guide (GPU queues, env setup on remote machine) _(2026-08-07)_
- [ ] @Abdoul — Make an SSH key for Babel/Bridges that the Hermes agent can use _(2026-08-07)_
- [ ] @Abdoul — Set up cron jobs to monitor experiments _(2026-08-07)_
- [ ] @Abdoul — Run failure analysis using pre-made prompt _(2026-08-07)_
- [ ] @Abdoul — Aim for first full run of OpenCUA on Babel _(2026-08-07)_
- [ ] @Abdoul — Sign off Phase 0 / `GROUNDING_MANIFEST.md` _(2026-07-10)_
- [ ] @Abdoul — Complete oracle → handoff refactor (currently WIP safety checkpoint) _(2026-W33)_
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo _(2026-08-14)_
- [ ] @Raghav — Find a method to transform human OSWorld-Human notes into more accurate step-by-step instructions to raise human-agent success rate _(2026-08-07/14)_
- [ ] @Raghav — Investigate and document OSWorld initialization bugs causing hanging states (e.g., Chrome not opening on setup) _(2026-08-07/14)_
- [ ] @Raghav — Manually annotate the agreed-upon set of ~10 traces (one OpenCUA model) _(2026-08-07)_
- [ ] @Abdoul — Manually annotate the same set of ~10 traces; compare with Raghav and Judge for inter-annotator agreement _(2026-08-07)_
- [ ] @Amaad — Set up Hermes Agent; create `Skill.md` for onboarding a new idea, including instructions for accessing/updating meeting docs via Google Workspace CLI; share with team _(2026-08-07)_
- [ ] @Amaad — After trajectories are collected, ask an agent to estimate frontier-model error-analysis cost (input/output tokens); proceed if ≤ $25, check with Matt if more _(2026-08-07)_
- [ ] @Matt — Provide OpenAI API access to team _(2026-08-14)_
- [ ] @Abdoul — SURA re-application _(2026-06-24)_

## Open questions

- Why is Chrome not opened on setup in OSWorld initialization? What other environment initialization bugs exist? _(2026-08-14)_
- Do incomplete human steps in OSWorld-Human systematically skew success/failure rates, and how should they be handled? _(2026-08-14)_
- How should the failure taxonomy be updated, and should prioritization weight step-of-occurrence, downstream impact, or a custom function? _(2026-08-14)_
- Has anyone already answered: *how much do successful (gold) trajectories improve automated error analysis, and what trajectory properties drive that improvement?* _(2026-08-14)_
- Is OSWorld still a relevant benchmark now that frontier models are evaluated on v2.0? Is error analysis only valuable for small models? _(2026-08-07)_
- If we run OSWorld with a frontier model that sees the OSWorld-Human notes, do we get ~100% success? If not, why not? _(2026-08-07)_
- What is the SOTA for small models on GUI grounding and on pixel-based computer use? _(2026-08-07)_
- How do we definitively distinguish perception/grounding errors from cognitive/planning errors in automated analysis? _(2026-08-07)_
- What counts as "small" for this project — 0.8B? 3B? 7B? 9B? _(2026-08-07)_
- Do we care about open-weights (QwenVL) vs. fully open-source (Molmo) distinction, and should that differentiate the work? _(2026-08-07)_
- Do CUAs perform worse when given screenshot context? If so, why? _(2026-06-24)_
- Is there value in allowing a pixel-only GUI agent to use code (CodeAct-style)? _(2026-06-24)_

## Technologies & tools discussed

- **Models:** UITARS-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B (CUA), Qwen3.5-VL 9B (judge), Sonnet 4.6 (judge), Opus 5 (frontier ceiling run, ~$150 for 10 tasks)
- **Benchmarks/Datasets:** OSWorld, OSWorld-Human (`WukLab/osworld-human`), OSWorld-G, OSWorld-Verified, ScreenSpot V2, WebArena (179 human Playwright traces), VisualWebArena (233 human Playwright traces), ClawBench, A3/AITK, OmniGUI, VideoCUA/CUA-Suite, UI-Vision, Mind2Web, WebLINX (BrowserGym-integrated), Android in the Wild (AITW), WebChain, PC Agent-E, TheAgentCompany, Mind2Web
- **Compute:** Babel (L40S GPUs), PSC Bridges-2 (GPU-shared, node v016, `cis260099p`), Slurm
- **Infra:** vLLM 0.11.0 (CUDA 12.6; do not use 0.23/0.12.0), OpenCUA ([github.com/xlang-ai/OpenCUA](https://github.com/xlang-ai/OpenCUA)), BrowserGym, `module load cuda/12.6.1`
- **Pixel Agent repo:** [github.com/MaximusAnax/pixel_agent](https://github.com/MaximusAnax/pixel_agent)
- **Papers referenced:**
  - CUADebug: [arXiv:2608.02643](https://arxiv.org/abs/2608.02643) _(2026-08-14; concurrent work)_
  - *Beyond the Final Answer* — tool-augmented agent reasoning trajectories _(2026-08-14)_
  - *How benchmarks mis-score*: [arXiv:2607.28367](https://arxiv.org/abs/2607.28367) _(2026-08-14)_
  - OSWorld-Human: [arXiv:2506.16042](https://arxiv.org/pdf/2506.16042)
  - Error analysis draft: [arXiv:2606.31270](https://arxiv.org/pdf/2606.31270)
  - TheAgentCompany: [arXiv:2412.14161](https://arxiv.org/pdf/2412.14161)
  - AI/Human Workflow Comparison: [arXiv:2510.22780v2](https://arxiv.org/abs/2510.22780v2)
  - OSWorld-G: [arXiv:2505.13227](https://arxiv.org/pdf/2505.13227)
  - GUI-Perturbed: [arXiv:2604.14262](https://arxiv.org/pdf/2604.14262)
  - CUA-Suite: [arXiv:2603.24440](https://arxiv.org/abs/2603.24440)
  - Stable Diffusion 3: [arXiv:2403.03206](https://arxiv.org/pdf/2403.03206)
  - Qwen3-VL Technical Report: [arXiv:2511.21631](https://arxiv.org/pdf/2511.21631)
  - ClawBench: [arXiv:2604.08523](https://arxiv.org/abs/2604.08523)
  - A3/AITK: [arXiv:2501.01149](https://arxiv.org/abs/2501.01149)
  - OmniGUI: [arXiv:2605.18758](https://arxiv.org/abs/2605.18758)
  - WebChain: [arXiv:2603.05295](https://arxiv.org/abs/2603.05295)
  - PC Agent-E: [arXiv:2505.13909](https://arxiv.org/abs/2505.13909)

## Research directions

- **OSWorld error analysis** — primary near-term focus; goal: reusable framework using gold/human trajectories to improve automated error analysis; answer how much gold trajectories help and what trajectory properties matter _(2026-08-14)_
- **Benchmark survey for human trajectories**: Tier 1 targets — OSWorld-Human, WebArena, VisualWebArena, ClawBench, A3; Tier 2 — OmniGUI, VideoCUA/CUA-Suite, WebChain, Mind2Web, WebLINX, AITW, UI-Vision, PC Agent-E _(2026-08-14)_
- **Inter-annotator agreement study**: Abdoul vs. Raghav vs. Judge (Sonnet 4.6) on ~10 manually selected traces _(2026-08-07/14)_
- **Release proper OSWorld-Human dataset** with full trajectories (blocked by benchmark drift concern) _(2026-08-07)_
- **Better CUA — generation-based** (e.g., diffusion grounding) _(2026-08-07)_
- **Better CUA — small model** (pixel-only, laptop/edge-scale) _(2026-08-07)_
- **Process Reward Models** (step-level verification): OSWorld-Verified + "Let's verify step by step" _(2026-08-07)_
- **Adaptive test-time compute** for small models (e.g., ReVL recursive grounding) _(2026-08-07)_
- **Fully open-source CUA**: differentiate from Qwen-based work using Molmo-class backbone _(2026-08-07)_
- **Streaming visual observations** — compressed memory, frame-difference summaries, or learned temporal representations _(2026-06-24)_
- **Harness design as a research variable** — observe-plan-act loop, memory, retries, action abstraction, subgoals, self-checking _(2026-06-24)_
- **RL training for small VLM agents** — after establishing imitation-learning baseline _(2026-06-24)_
