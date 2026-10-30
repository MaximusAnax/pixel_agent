# Project state

> Auto-synthesized on 2026-10-30 by `ops/synthesize_state.py` (extractive mode). The compact digest also lives in `AGENTS.md` so Hermes loads it every turn. Edit upstream sources (meeting notes in `ops/meetings/`, weekly reports in `ops/reports/`), not this file — it is regenerated.

## Current snapshot

- **As of:** 2026-10-30
- **Most recent meeting:** 2026-10-30
- **Meetings folded in:** 2026-06-24, 2026-07-10, 2026-08-07, 2026-08-14, 2026-08-21, 2026-08-29, 2026-09-04, 2026-09-11, 2026-09-18, 2026-09-25, 2026-10-02, 2026-10-09, 2026-10-16, 2026-10-23, 2026-10-30

## Recent progress

From **2026-W44.md** (At a glance):
- **Merged PRs:** 0 | **Commits:** 1 | **Lines changed:** +807/−39 across 5 files
- Sixth consecutive maintenance week; only post-meeting state sync committed; no experiment runs, no new artifacts
- Carry-forward blockers remain: Oracle → handoff refactor still WIP; PXA-024 (frontier-model Human Agent ceiling run) has now slipped **six** consecutive weeks with no start date confirmed
- Labeling schema (PXA-001/002/003/016) and failure-taxonomy compendium stable; no regressions
- State-synthesis pipeline (`ops/synthesize_state.py`) and `AGENTS.md` digest loop operating normally

From **2026-10-30 meeting** (notable updates):
- Attendees not explicitly listed
- **Amaad departing** to `withampersand.ai`; Matt will recruit **two** new project members
- **Subgoal analysis** introduced as new primary research direction: break gold and agent trajectories into subgoals; judge whether agent completed each subgoal (even via different path); use topological ordering (flagged as extremely tricky); fallback to agent's own reasoning subgoals when gold provides no useful structure
- **Raghav observation**: screenshots alone are not helping error analysis — text descriptions of steps are more informative; gold trajectory only helps when it diverges from agent trajectory at exact moment of error
- **System One (Jev) model exploration**: fast/cheap model to explore many possible trajectory paths (beam search, stochastic beam search, backtracking); Jev now has a bounding box API — could enable large fanout for error analysis or task solving
- No new experiment data; no PRs merged

## Decisions (cumulative)

- Use **UITARS-72B** as grounding model for OSWorld runs; current success rate: **60/361 tasks** _(2026-08-07/14)_
- Use **Sonnet 4.6** as LLM judge over OpenCUA-3B and -7B traces _(2026-08-14/21)_
- **Three-judge ensemble decided**: Claude, GPT-Luna, offline Qwen-7B _(formalized 2026-10-23)_
- **OSWorld-Human not yet folded in** to the judge pipeline — pending Oracle Agent implementation _(2026-08-14/21)_
- Judge should receive: task description JSON, reference trajectory, predicted trajectory, OSWorld metric score, **and** relevant evaluator metric functions (e.g., `is_expected_tabs` source from `desktop_env/evaluators/metrics`) _(confirmed through 2026-10-30)_
- **Judge logic to incorporate both human and model screenshots per step** in the trace _(confirmed through 2026-10-30)_
- **Start pilot annotation with existing paired taxonomy CSV** before scaling up — path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv` _(confirmed through 2026-10-30)_
- Error prioritization to be explored along three axes: step of occurrence, downstream impact, and a to-be-designed prioritization function _(ongoing; no resolution as of 2026-10-30)_
- **NeurIPS concurrent-work policy**: papers appearing after March 1 2025 (including CUADebug, arXiv:2608.02643) are considered concurrent; comparison not required _(confirmed 2026-09-25)_
- **All-applicable labeling**: judge selects all applicable failure modes per episode rather than primary/secondary only _(2026-08-14, PXA-001/002/003/016)_
- Use **vLLM 0.11.0** as the lab-standard version on Bridges (CUDA 12.6 compatible; do not use vLLM 0.23 which requires CUDA 13, or 0.12.0 which has no prebuilt wheel) _(confirmed working through 2026-10-30)_
- Keep OSWorld VMs and inference both on Babel/Bridges — not split with AWS _(confirmed through 2026-10-30)_
- CUA agent: **Qwen3.5-VL 0.8B**; Judge: **Qwen3.5-VL 9B** on Babel L40S GPUs _(2026-08-07)_
- Cost threshold: if frontier-model error analysis costs ≤ $25, proceed without checking in with Matt; if more, check in first _(confirmed through 2026-10-30)_
- **Bring two new people into the project** — Matt to recruit two additional members following Amaad's departure _(updated 2026-10-30)_
- **Current milestone = annotation-ready infrastructure** — OSWorld task/eval context, Human Agent screenshots for annotators + multimodal judge, mockup-approved dual-trace UI, provisional rejudge `osworld_v1` _(2026-07-10)_
- **Provisional judge vs human gold** — versioned judge labels (`judge_context_version`) are reference only; `annotations.json` is gold-in-progress _(2026-07-10)_
- **Human reference is non-binding** — full human sequence for context; no forced step alignment to agent path _(2026-07-10)_
- **Rejudge waits for Human Agent** — multimodal `osworld_v1` only after `oracle_status` ready/partial _(2026-07-10)_
- **Grounding freeze** — after Abdoul sign-off, files in `errorAnalysis/docs/GROUNDING_MANIFEST.md` must not be edited without a new approved plan _(2026-07-10)_
- **Start from existing HuggingFace trajectories** before generating new ones _(2026-06-24)_
- **Focus models for trajectory review**: OpenCUA, Kimi, Sonnet 4.5 — not older models _(2026-06-24)_
- **Tier 1 priority benchmarks** for human ↔ agent comparison: OSWorld-Human, WebArena Human Trajectories, VisualWebArena Human Trajectories, ClawBench, A3/AITK _(formalized 2026-10-16)_
- **Tier 2 benchmarks** (useful for extending trajectory metrics / validating human behavior patterns): OmniGUI, VideoCUA/CUA-Suite, WebChain, Mind2Web, WebLINX, AITW, UI-Vision, PC Agent-E _(formalized 2026-10-16)_
- Canonical task set and order to be fixed before further annotation runs _(2026-09-18)_
- Raghav and Abdoul to agree on a **common data format** for sharing trajectories _(2026-09-18)_
- **Primary research goal**: create a reusable framework for automated CUA error analysis using gold/human trajectories; answer *How much do gold trajectories improve automated error analysis, and what trajectory properties drive that improvement?* _(confirmed 2026-10-30)_
- **Subgoal analysis** is the current primary direction for using gold trajectories in error analysis; topological ordering flagged as extremely tricky _(2026-10-30, provisional)_

## Open feedback & critiques

- **Screenshots alone are not helping error analysis** — text descriptions of steps are more informative; gold trajectory only helps when it diverges from agent trajectory at the exact moment of error _(2026-10-30)_
- **Human evaluators can be wrong**: in one case, referential expression about what to click was incorrect but model clicked correctly; judge called it "reasoning" error, human annotator called it "grounding" error — judge vs. human disagreement is non-trivial _(ongoing)_
- **OSWorld-Human incomplete steps** cause failures: e.g., instructions say to type in a search bar but never say to press Enter _(ongoing)_
- **Model races ahead** while screen is still loading from the previous action _(ongoing)_
- **OSWorld initialization errors**: initial environment not loaded properly (e.g., Chrome not opened on setup) _(ongoing)_
- **CUADebug** (arXiv:2608.02643) is very similar in scope — uses failure-mode taxonomy + automated analysis; our novelty relative to it is the use of human/gold trajectories _(ongoing)_
- Frontier-model costs high: Opus 5 ran ~$150 for high usage; 2/10 tasks failed _(ongoing)_
- Benchmark drift concern: websites/software drift over time, invalidating trajectories _(ongoing)_
- Relevance concern: frontier models evaluated on OSWorld v2.0 — is the benchmark still meaningful for small models? _(ongoing)_
- Historical screenshots can confuse models even when action history is included _(ongoing)_
- Planning/reflection phases often take many more steps than necessary on medium/hard tasks _(ongoing)_
- Icon accuracy is the main differentiator across grounding benchmarks (21–72% range); text grounding is relatively saturated (70–82%) _(ongoing)_
- Post-training small models may be difficult since they are likely distillation-trained _(ongoing)_
- **Multi-agent parallel exploration** trade-off: interacting with a CUA is not side-effect-free (unlike reading a codebase), so dispatching parallel subagents risks conflicting state changes; higher cost/latency vs. better UI coverage _(ongoing)_
- Subgoal analysis edge case: tasks with no meaningful subgoals (e.g., "Open most recently closed tab" via Ctrl+Shift+T) provide no useful gold structure _(2026-10-30)_

## Ideas on the table

- **Subgoal analysis (primary new direction):** Break gold and agent trajectories into subgoals; optionally apply topological ordering (extremely tricky); judge whether agent completed each subgoal via any path; use agent's own reasoning subgoals as fallback when gold provides no useful structure _(2026-10-30)_
- **System One (Jev) model exploration:** Use fast/cheap System One model to explore many possible trajectory paths (beam search, stochastic beam search, backtracking) for richer error analysis or task solving; Jev now has a bounding box API _(2026-10-30)_
- **Inter-annotator agreement study**: Raghav and Abdoul each independently annotate the same ~10-trace failure set; compute agreement across pairs: (human A / human B), (human A / judge with gold), (human B / judge with gold), (judge with gold / judge without gold) _(ongoing)_
- **Gold trajectory generation via frontier model**: where only human notes exist (OSWorld-Human), prompt a frontier model with those notes during live task execution; target ~100% success rate as gold standard _(ongoing)_
- **Failure mode prioritization function**: weight by step of occurrence (earlier = higher importance) and downstream failure count as impact signal _(ongoing)_
- **"Oracle Agent"** that replays human actions in OpenCUA to generate a screenshot for every human step _(ongoing)_
- **Consolidated HTML annotation viewer** with: task ID display, canonical task ordering, real task description from JSON, multi-failure-mode support, enlarged image on click, side-by-side AI vs. human trace, optional reasoning trace toggle (collapsed by default), always-shown actions, left-nav with category/prompt/step count, "failing step" integer field _(ongoing)_
- Give the Judge both agent and human trajectory; ask it to select **all applicable failure modes** _(ongoing)_
- Run OSWorld with a frontier model reading OSWorld-Human notes → check if it achieves ~100%; diagnose why not _(ongoing)_
- **Multi-agent parallel exploration:** Dispatch multiple subagents to explore different UI paths simultaneously; store results in a vector/text DB for future tasks in the same UI; use separate Chrome instances to reduce side-effects _(ongoing)_
- **AI-assisted idea generation workflow**: ask model to critique a specific paper; ask for 10 variants of an implementation idea; ask for 10 most closely related papers and how each limits novelty _(ongoing)_
- **Multi-path human trajectory analysis**: A3 has ~3 valid human trajectories per task, enabling strategy variation analysis _(ongoing)_
- Generate grounding labels with an image diffusion model (Stable Diffusion 3); detect generated marker via traditional CV or a highly unusual synthetic pattern (e.g., houndstooth) _(ongoing)_
- **Compressed GUI state / learned memory:** Compress GUI state history into a learned representation rather than raw screenshots; helps with pop-ups/ads by detecting state changes without extra actions _(ongoing)_
- **Dual-model perception + planning split:** One model for candidate element selection (grounding), another for action output (planning); optionally a third for tool calls / web search _(ongoing)_
- **RL for best-action prediction:** Train model to predict post-action state; reward best choice; supervise reasoning traces _(ongoing)_
- **Instruction enhancement agent:** LLM enriches original task instruction with broad directions and success metrics before passing to CUA _(ongoing)_
- **Rewarding efficient thinking traces** to reduce unnecessary planning steps _(ongoing)_
- World models for planning in CUA; allow world model to explore new software and self-generate training data _(ongoing)_
- Use YouTube computer-use tutorial videos as training data (cf. Gemma 4 video training; CUA-Suite) _(ongoing)_
- **Special "call another model" action**: main VLM acts, specialist VLM grounds/creates bounding boxes on demand _(ongoing)_
- **Auto-research agents** — spin up agents to survey literature and brainstorm (Karpathy-style); P3/later _(ongoing)_
- **Adaptive test-time compute** for small models (e.g., ReVL recursive grounding approach) _(ongoing)_
- **Fully open-source CUA**: differentiate from Qwen-based work using fully open-provenance backbone (e.g., Molmo) _(ongoing)_
- **Process Reward Models** (step-level verification): OSWorld-Verified + "Let's verify step by step" _(ongoing)_
- **Orthogonal icon-meaning data sources** — PowerPoint documentation, webpage alt-text, etc. _(ongoing)_
- Agentic trajectory scraping from videos + synthetic augmentation to create new traces _(ongoing)_
- Synthetic RL environment task generation _(ongoing)_
- **Extract detailed text descriptions of steps from screenshots** for richer judge/error analysis input _(2026-10-30, provisional)_

## Action items

- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace _(confirmed through 2026-10-30)_
- [ ] @Abdoul — Continue editing HTML viewer to surface judge assessments alongside paired trajectories _(ongoing)_
- [ ] @Abdoul — Improve judge calibration on 5 pilot tasks: human-agent succeeded, OpenCUA-3B and -7B both failed, judge produced a failure-mode conclusion _(ongoing)_
- [ ] @Abdoul — Refine taxonomy discovery labels starting from pilot path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv` _(ongoing)_
- [ ] @Abdoul — Continue reading failure analysis papers; survey how existing work categorizes failure modes (including CUADebug arXiv:2608.02643); determine whether existing error analysis on non-OSWorld benchmarks renders contribution non-novel _(ongoing)_
- [ ] @Abdoul — Set up OSWorld evaluation script to output per-trace success/failure metadata visible to humans and passed to the judge (include task description JSON + evaluator metric functions from `desktop_env/evaluators/metrics`) _(ongoing)_
- [ ] @Abdoul — Make OSWorld-Human traces visible alongside OpenCUA traces in the annotation viewer _(ongoing)_
- [ ] @Abdoul — Write up Babel quick-start guide (GPU queues, env setup on remote machine) _(ongoing)_
- [ ] @Abdoul — Make an SSH key for Babel/Bridges that the Hermes agent can use _(ongoing)_
- [ ] @Abdoul — Complete oracle → handoff refactor (currently WIP safety checkpoint) _(ongoing)_
- [ ] @Abdoul — SURA re-application _(ongoing)_
- [ ] @Abdoul — Sign off Phase 0 / `GROUNDING_MANIFEST.md` _(ongoing)_
- [ ] @Abdoul — Manually annotate the same ~10 pilot traces as Raghav for inter-annotator agreement comparison _(ongoing)_
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo; start with pilot trajectories at `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv` _(ongoing)_
- [ ] @Raghav — Find a method to transform OSWorld-Human instructions into more complete/accurate step-by-step instructions to raise Oracle Agent success rate (e.g., handle missing "press Enter" steps) _(ongoing)_
- [ ] @Raghav — Investigate and document OSWorld initialization bugs causing hanging states (e.g., Chrome not opening on setup) _(ongoing)_
- [ ] @Raghav — Build Oracle Agent within OpenCUA that replays human actions and generates a screenshot per step _(ongoing)_
- [ ] @Raghav — Manually annotate the same ~10 pilot traces as Abdoul for inter-annotator agreement study _(ongoing)_
- [ ] @Raghav — Dive deeper into human agent; start with pilot trajectories in repo _(ongoing)_
- [ ] @Raghav + @Abdoul — Read failure analysis papers to survey existing failure categorization schemes and inform taxonomy updates _(ongoing)_
- [ ] @Raghav + @Abdoul — Agree on a common data format for sharing trajectories _(ongoing)_
- [ ] @Raghav + @Abdoul — Add evaluation-script output (success/fail metadata + evaluator function descriptions from `desktop_env/evaluators/metrics`) to judge input and to the human review viewer _(ongoing)_
- [ ] @Raghav + @Abdoul — Consolidate HTML annotation viewer features: task ID display, canonical task ordering, real task description from JSON, multi-failure-mode support, enlarged image on click, side-by-side AI vs. human trace, optional reasoning trace toggle (collapsed by default), always-shown actions, left-nav with category/prompt/step count, "failing step" integer field _(ongoing)_
- [ ] @Raghav + @Abdoul — After all trajectories are collected, ask an agent to estimate frontier-model judge cost (input/output tokens); proceed if ≤ $25, else check with Matt _(ongoing)_
- [ ] @Raghav + @Abdoul — Explore subgoal analysis: break gold and agent trajectories into subgoals; assess feasibility of topological ordering; identify fallback strategy for single-step tasks _(2026-10-30)_
- [ ] @Matt — Provide OpenAI API access to team _(ongoing)_
- [ ] @Matt — Meet with two additional potential project members and onboard them _(updated 2026-10-30)_

## Open questions

- Does existing error analysis on benchmarks other than OSWorld already answer the team's core research question, rendering the approach non-novel? _(ongoing)_
- Has anyone already answered: *how much do successful (gold) trajectories improve automated error analysis, and what trajectory properties drive that improvement?* _(ongoing)_
- Does subgoal analysis (with topological ordering) remain feasible given available data, or must it rely entirely on the agent's own reasoning subgoals? _(2026-10-30)_
- What happens when a gold trajectory has no meaningful subgoals (e.g., single-shortcut tasks like "Open most recently closed tab" via Ctrl+Shift+T)? _(2026-10-30)_
- Can text descriptions of steps extracted from screenshots replace raw screenshots as judge input, and how should they be generated? _(2026-10-30, provisional)_
- How should the failure taxonomy be updated given observations from OSWorld-Human trajectories? _(ongoing)_
- Which failure-mode prioritization strategy is most appropriate: step order, downstream impact, or a custom function? _(ongoing)_
- When judge and human annotator disagree on error category (e.g., "reasoning" vs. "grounding"), how do we arbitrate — and does this reflect a fundamental ambiguity in the taxonomy? _(ongoing)_
- Why is Chrome not opened on setup in OSWorld initialization? What other environment initialization bugs exist? _(ongoing)_
- Do incomplete human steps in OSWorld-Human systematically skew success/failure rates, and how should they be handled? _(ongoing)_
- What is the best method to transform incomplete OSWorld-Human instructions into reliable gold trajectories that achieve ~100% success rate? _(ongoing)_
- Can a frontier model achieve ~100% success on OSWorld tasks when guided by OSWorld-Human notes? If not, why not? _(ongoing)_
- Is OSWorld still a relevant benchmark now that frontier models are evaluated on v2.0? Is error analysis only valuable for small models? _(ongoing)_
- How many of the ~300 A3/AITK human trajectories are publicly downloadable as a standalone archive? _(ongoing)_
- Can ClawBench human reference runs be bulk-downloaded before committing to it as a Tier 1 benchmark? _(ongoing)_
- What is the SOTA for small models (≤7B) on GUI grounding (ScreenSpot V2, OSWorld-G) and on pixel-based computer use (OSWorld-Verified)? _(ongoing)_
- How do we definitively distinguish perception/grounding errors from cognitive/planning errors in automated analysis? _(ongoing)_
- What counts as "small" for this project — 0.8B? 2B? 4B? 7B? _(ongoing)_
- Do we care about open-weights (QwenVL) vs. fully open-source (Molmo) distinction, and should that differentiate the work? _(ongoing)_
- Does giving a VLM screenshot history actually hurt performance, and if so, why? Are any current models trained to understand sequences of frames? _(ongoing)_
- Is there value in allowing a pixel-only GUI agent to use code (CodeAct-style)? _(ongoing)_
- Do small VLMs exhibit qualitatively different failure modes than large VLMs, and if so, can those failures be fixed via harness or training changes? _(ongoing)_
- Can multi-agent parallel UI exploration be made practical given that CUA interactions are not side-effect-free? _(ongoing)_
- Could multiple Chrome instances fully isolate side effects during multi-subagent UI exploration? _(ongoing)_

## Technologies & tools discussed

- **Models:** UITARS-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B (CUA), Qwen3.5-VL 9B / 32B (judge/grounding), Sonnet 4.6 (judge), Opus 5 (frontier ceiling run, ~$150 for high usage); Claude, GPT-Luna, Qwen 7B (offline) — three-judge ensemble decided; Jev / System One model (fast/cheap, now has bounding box API)
- **Benchmarks/Datasets:** OSWorld, OSWorld-Human (`WukLab/osworld-human`), OSWorld-G, OSWorld-Verified, ScreenSpot V2, ScreenSpot Pro, WebArena (179 human Playwright traces), VisualWebArena (233 human Playwright traces), ClawBench, A3/AITK (~3 trajectories/task), OmniGUI (708 expert episodes), VideoCUA/CUA-Suite (~10K human-demonstrated tasks), UI-Vision, Mind2Web, WebLINX (BrowserGym-integrated), Android in the Wild (AITW, ~715K episodes), WebChain (31,725 traces), PC Agent-E (312 traces), AndroidWorld
- **Compute:** Babel (L40S GPUs), PSC Bridges-2 (GPU-shared, node v016, `cis260099p`), Slurm
- **Bridges-2 hardware (for reference):** 10× Cray HPE XD670 (8× H100-80GB, 2048GB RAM); 3× HPE DL380aG12 (8× L40S-48GB, 1024GB RAM); 24× original nodes (8× V100-32GB, 512GB RAM); migrated nodes (8× V100-16GB, 192GB RAM); 1× DGX-2 (16× V100-32GB, 1.5TB RAM)
- **Infra:** vLLM 0.11.0 (CUDA 12.6 confirmed; do not use 0.23/0.12.0), OpenCUA ([github.com/xlang-ai/OpenCUA](https://github.com/xlang-ai/OpenCUA)), BrowserGym, `module load cuda/12.6.1`
- **Frameworks discussed:** LangGraph, Anthropic Agent SDK, Google ADK
- **Pixel Agent repo:** [github.com/MaximusAnax/pixel_agent](https://github.com/MaximusAnax/pixel_agent)
- **Research summary doc:** `https://github.com/raghav3003/pixel_agent/blob/goldjudge-stage/docs/research/2026-09-24-project-summary.md`
- **Papers referenced:**
  - CUADebug: [arXiv:2608.02643](https://arxiv.org/abs/2608.02643) _(concurrent work)_
  - *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* _(baseline comparison for core paper direction)_
  - *How benchmarks mis-score*: [arXiv:2607.28367](https://arxiv.org/abs/2607.28367)
  - *Learning from Online Videos at Inference Time for Computer-Use Agents*
  - *Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs*
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
  - AITW: [arXiv:2307.10088](https://arxiv.org/abs/2307.10088)
  - UI-Vision: [arXiv:2503.15661](https://arxiv.org/abs/2503.15661)
  - *Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding*
