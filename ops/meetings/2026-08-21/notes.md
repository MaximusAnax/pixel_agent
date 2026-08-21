# Meeting notes — 2026-08-21

## Attendees
- Raghav
- Abdoul
- Amaad
- Matt (referenced, not confirmed present)

## Technologies discussed
- **Models:** UITARS-72B (grounding), OpenCUA-3B, OpenCUA-7B, Sonnet-4.6 (judge), Qwen3.5-VL 0.8B / 9B, Opus 5
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, WebArena, VisualWebArena, ClawBench, A3 / AITK, ScreenSpot V2
- **Datasets (human trajectories):** OmniGUI, VideoCUA / CUA-Suite, UI-Vision, Mind2Web, WebLINX, Android in the Wild (AITW), WebChain, PC Agent-E
- **Infrastructure:** Babel (L40S GPUs), PSC Bridges-2 (`cis260099p`, GPU-shared), Slurm, vLLM 0.11.0, CUDA 12.6
- **Papers discussed:**
  - CUADebug [arXiv:2608.02643]
  - OSWorld-Human [arXiv:2506.16042]
  - Error analysis paper [arXiv:2606.31270]
  - *How benchmarks mis-score* [arXiv:2607.28367]
  - *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents*
  - TheAgentCompany [arXiv:2412.14161]
  - CUA-Suite [arXiv:2603.24440]
  - OSWorld-G [arXiv:2505.13227]
  - GUI-Perturbed [arXiv:2604.14262]
  - WebChain [arXiv:2603.05295]
  - Qwen3-VL Technical Report [arXiv:2511.21631]
  - *Learning from Online Videos at Inference Time for Computer-Use Agents*
  - *Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs*

## Decisions made
- **vLLM version:** Use vLLM 0.11.0 on Bridges (0.12.0 wheel unavailable; 0.23 incompatible with CUDA 12.6)
- **Judge model:** Sonnet-4.6 (for LLM-as-judge over OpenCUA traces)
- **CUA models in use:** OpenCUA-3B and OpenCUA-7B traces are the primary evaluation subjects
- **OSWorld-Human is not yet folded into the judge pipeline** — still pending Oracle Agent implementation
- **NeurIPS concurrent-work policy acknowledged:** Papers after March 1, 2025 are concurrent; no comparison required
- **Priority benchmarks for Tier 1 human ↔ agent comparison:** OSWorld-Human, WebArena, VisualWebArena, ClawBench, A3
- **Keep all compute on Bridges/Babel** (OSWorld VMs + inference co-located, not split to AWS)
- **Cost threshold for frontier judge runs:** Proceed autonomously if ≤ ~$25; check with Matt if more expensive

## Feedback / critiques
- OSWorld-Human instructions are incomplete — e.g., steps tell the model to type in a search bar but omit pressing Enter; model moves to the next action while the screen is still loading
- OSWorld initialization errors cause hanging states (e.g., Chrome not opened on setup) — reduces reliability of gold-label generation
- UITARS-72B achieved only 60/361 tasks (≈16.6%) using OSWorld-Human as a guide, partly due to the above issues
- Frontier models (Opus 5 at $150 for high usage, 2/10 tasks failed) raise cost concerns for scale
- CUADebug [2608.02643] is very similar to the team's existing approach (failure taxonomy + analysis); novelty must rest on use of human/gold trajectories

## Ideas considered
- **Oracle Agent:** Run OSWorld with a frontier model that reads OSWorld-Human notes to generate near-perfect gold trajectories (target: 100% success rate); use these where human trajectories are absent
- **LLM-as-judge with gold trajectories:** Provide judge with both agent and human trajectory; ask it to select *all* applicable failure modes (not just primary/secondary) from the taxonomy
- **Failure mode prioritization schemes (open):** by step of occurrence, by downstream impact, or by a custom priority function
- **Image-diffusion-based grounding:** Use a model (e.g., Stable Diffusion 3) to mark up screenshots; detect unusual generated shapes (e.g., houndstooth pattern) via traditional CV techniques
- **Learned GUI state / compressed memory:** Compress GUI history rather than passing all screenshots; helps with sudden ads/pop-ups and long-horizon context confusion
- **Dual-model architecture:** Separate perception (grounding) from planning; optionally a third model for tool calls / documentation lookup
- **RL for CUA:** Teach model to predict state after candidate actions; supervise reasoning traces
- **Efficient thinking reward:** Penalize unnecessary reasoning steps to make CUA more efficient
- **YouTube tutorial training:** Train on video demonstrations of computer use (related to CUA-Suite)
- **AI-assisted idea generation workflow documented:**
  - Ask model to critique a specific paper
  - Ask for 10 variants of a specific implementation idea
  - Ask for 10 most closely related papers to a given idea and how each limits novelty

## Ideas & research directions
- **Error analysis framework (core project):** Reusable framework for CUA error analysis using gold/human trajectories; answer: *how much do gold trajectories improve automated error analysis, and what trajectory properties drive that improvement?*
- **Inter-annotator agreement study:** Raghav and Abdoul each manually annotate the same ~10 traces; compute agreement between human1/human2, human1/judge (with gold), human2/judge (with gold), judge(with gold)/judge(without gold)
- **Streaming visual observations for CUAs:** Compressed memory / frame-difference summaries for scrolling, video-watching, and dynamic UI tasks — relevant for both small and frontier models
- **Small pixel-only VLM agent:** Baseline using imitation learning → then RL; iterate on harness design (observe-plan-act loop, memory, retries, subgoals)
- **Auto-research agent** (P3 / later): Spin up agents to survey literature and brainstorm on a research problem (à la Karpathy's auto-research)

## Action items
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo
- [ ] @Raghav — Find a method to transform OSWorld-Human instructions into more complete/accurate steps that raise Oracle Agent success rate (e.g., handle missing "press Enter" steps)
- [ ] @Raghav — Investigate and document OSWorld initialization bugs causing hanging states (e.g., Chrome not opened on setup)
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks meeting criteria: (1) human agent succeeded, (2) OpenCUA-7B and -3B both failed, (3) judge produced a failure-mode conclusion
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Read failure analysis papers to survey existing failure categorization schemes; update taxonomy as appropriate
- [ ] @Abdoul — Read related work on benchmarks beyond OSWorld to assess whether existing error analysis renders the team's approach non-novel
- [ ] @Amaad — For each Tier 1 benchmark, determine exactly what exists in the human trajectories (real actions vs. notes)
- [ ] @Matt — Give OpenAI API access to the team
- [ ] @Raghav + @Abdoul — Manually annotate the same ~10 pilot traces (path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`) and compute inter-annotator agreement
- [ ] @Raghav + @Abdoul — Implement Oracle Agent that replays human OSWorld-Human actions inside the OpenCUA environment to generate screenshots for every step
- [ ] @Raghav + @Abdoul — Add evaluation-script output (success/fail metadata + evaluator function descriptions from `desktop_env/evaluators/metrics`) to judge input and to the human review viewer
- [ ] @Raghav + @Abdoul — Consolidate HTML annotation viewer features: task ID display, canonical task ordering, real task description from JSON, multi-failure-mode support, enlarged image on click, side-by-side AI vs. human trace, optional reasoning trace toggle, always-shown actions, left-nav with category/prompt/step count, "failing step" integer field

## Open questions
- Does existing error analysis on benchmarks other than OSWorld already answer the team's core research question, rendering the approach non-novel?
- Is OSWorld still relevant as a benchmark given that frontier models are now evaluated on OSWorld v2.0 and small models dominate the error landscape?
- What is the lab-standard conda env, CUDA module, and vLLM version/wheel for serving OpenCUA on Bridges?
- Should failure modes be prioritized by step of occurrence, downstream impact, or a custom function — and who defines that function?
- Do CUAs perform worse when given screenshot history as context, and if so, why? Are any deployed models trained to understand sequential screen frames (video understanding)?
- How many of the ~300 A3/AITK human trajectories are publicly downloadable as a standalone archive?
- Can ClawBench human reference runs be bulk-downloaded before committing to it as a Tier 1 benchmark?
