# Meeting notes — 2026-10-16

## Attendees
- Raghav, Abdoul (confirmed from Raghav + Abdoul tab for most recent session)

## Technologies discussed
- **Models / Judges:** Claude (Sonnet-4.6), GPT-luna, Qwen 7B (offline), UITARS-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B / 9B / 32B
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, WebArena, VisualWebArena, ClawBench, A3/AITK, ScreenSpot V2
- **Datasets (human trajectories):** OmniGUI, VideoCUA/CUA-Suite, UI-Vision, Mind2Web, WebLINX, Android in the Wild (AITW), WebChain, PC Agent-E
- **Infrastructure:** Babel (L40S GPUs), PSC Bridges-2 (Slurm, CUDA 12.6.1), vLLM 0.11.0
- **Tools / Frameworks:** OSWorld benchmark env, HTML annotation viewer (Raghav + Abdoul each have one), Playwright traces (WebArena/VisualWebArena)
- **Papers mentioned:**
  - CUADebug `[2608.02643]`
  - OSWorld-Human `arXiv:2506.16042`
  - Error analysis paper `arXiv:2606.31270`
  - *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents*
  - GUI-Perturbed `arXiv:2604.14262`
  - CUA-Suite `arXiv:2603.24440`
  - OSWorld-G `arXiv:2505.13227`
  - ClawBench `arXiv:2604.08523`
  - A3/AITK `arXiv:2501.01149`
  - WebChain `arXiv:2603.05295`
  - *Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding*
  - Qwen3-VL Technical Report `arXiv:2511.21631`

## Decisions made
- **vLLM version on Bridges-2:** Use vLLM 0.11.0 (0.12.0 source-build fails; 0.23 requires CUDA 13 which conflicts with Bridges' CUDA 12.6.1)
- **Cluster strategy:** Keep OSWorld VMs and inference all on Bridges/Babel (not split with AWS)
- **Judge model:** Sonnet-4.6 judging OpenCUA-3B and OpenCUA-7B traces
- **Bring someone new into the project:** Yes, agreed
- **Cost threshold for frontier-model error analysis:** If estimated cost ≤ $25, proceed without checking with Matt; if more, check in first
- **Benchmark priority tiers:**
  - Tier 1: OSWorld-Human, WebArena Human Trajectories, VisualWebArena Human Trajectories, ClawBench, A3
  - Tier 2: OmniGUI, VideoCUA/CUA-Suite, WebChain, Mind2Web, WebLINX, AITW, UI-Vision, PC Agent-E

## Feedback / critiques
- Human annotators and LLM judges disagree on error type: in one case the referential expression was incorrect but the model clicked correctly — judge called it a "reasoning" error, human called it a "grounding" error
- OSWorld-Human instructions are incomplete (e.g. ask model to type in a search bar but never instruct it to press Enter), causing human agent failures
- UITARS-72B achieved only 60/361 tasks (≈17%) on OSWorld using OSWorld-Human as guide
- OSWorld initialization errors: initial environment sometimes not loaded properly; Chrome not opened on setup
- Model moves to next action while screen is still loading from previous action
- Historical screenshots can confuse models even when action history is included; unclear whether current VLMs are trained to understand sequential frames
- CUADebug `[2608.02643]` is very similar to the team's error-analysis direction — novelty must be clearly differentiated (use of human/gold trajectories)

## Ideas considered
- **Multi-agent exploration:** Dispatch subagents to explore different UI paths (e.g. each clicks a different tab); store exploration in a vector/text DB for future tasks within the same UI. Use multiple Chrome instances to avoid side-effects. Analogous to coding-agent codebase exploration but non-trivially different because CUA interactions have side-effects.
- **Diffusion-model grounding:** Use image generation model (e.g. Stable Diffusion 3) to mark up screenshots with an unusual visual pattern (e.g. houndstooth) to aid grounding; find the mark using traditional CV techniques
- **Memory for CUAs:** Compress GUI state rather than passing raw screenshots; helps with sudden ads/pop-ups by detecting state changes without new actions
- **Dual-model architecture:** Separate perception (grounding/candidate selection) from planning; optionally add a third model for tool calls (e.g. web search for documentation)
- **RL for action selection:** Train model to predict post-action state and nudge it toward the best action; supervise reasoning traces
- **Instruction enhancement:** Use an LLM to expand the original task instruction with broad directions and success metrics before the agent acts
- **YouTube tutorial training:** Train on computer-use tutorial videos (reference: *Learning from Online Videos at Inference Time for Computer Use Agents*)
- **Reward efficient thinking:** Reward concise/effective reasoning to reduce unnecessary steps in planning/reflection phases
- **Auto-research agent:** Spin up agents to explore literature and brainstorm (reference: Andrej Karpathy's auto-research concept) — marked P3/later
- **Agentic trajectory scraping from videos + synthetic augmentation** (Amaad)
- **Synthetic RL environment task generation** (Amaad)

## Ideas & research directions
- **Core paper direction — Error analysis with gold trajectories:**
  - Goal 1: Reusable framework for CUA error analysis using gold/human trajectories
  - Goal 2: Quantify how much gold trajectories improve automated error analysis, and what trajectory properties drive that improvement
  - Research question: For practitioners without resources for expensive human error analysis — how much do successful trajectories help an LLM judge?
  - Baseline comparison: *Beyond the Final Answer* (error analysis without golden traces)
- **Oracle Agent:** Run human OSWorld-Human actions inside OpenCUA env to generate per-step screenshots for the human trajectory
- **Gold trajectory generation from notes:** Run frontier model guided by OSWorld-Human notes; check whether 100% success rate is achievable; if not, investigate why
- **Judge prompt revision:** Ask judge to select *all* applicable failure modes (rather than primary/secondary), given both agent and human trajectory
- **Inter-annotator agreement study:** Raghav and Abdoul each manually annotate the same set of traces; compute agreement for human1/human2, human1/judge, human2/judge
- **AI-assisted idea generation techniques discussed:**
  - Ask a model to critique a paper: "What would you have done differently?"
  - Refine a specific idea: "Here are 10 ways I could implement X"
  - Novelty check: "Here are the 10 papers most closely related to my idea"

## Action items
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo
- [ ] @Raghav — Find a method to transform human trajectories into more accurate instructions (improve human-agent success rate)
- [ ] @Raghav — Investigate OSWorld initialization bugs causing hanging states (e.g. Chrome not opened on setup)
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 specific tasks where: human agent succeeded, both OpenCUA-7B and OpenCUA-3B failed, and judge produced a failure-mode conclusion
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Read more failure analysis papers; survey how existing work categorizes failure modes
- [ ] @Abdoul — Investigate broader set of related benchmarks to determine whether existing error analysis renders the team's approach non-novel
- [ ] @Matt — Give OpenAI API access to team
- [ ] @Raghav — Manually annotate a canonical set of ~10 traces (pilot set: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`)
- [ ] @Abdoul — Manually annotate the same ~10 traces; compute inter-annotator agreement
- [ ] @Amaad — For each benchmark identified, determine exactly what exists in the human trajectories (real browser actions vs. notes only) and extent to which modern CUA work still relies on each benchmark
- [ ] @Raghav — Dive deeper into human agent; start with pilot trajectories in repo
- [ ] @team — Update OSWorld evaluation script to output failure reason info (human-readable + for the judge), including task description JSON and relevant evaluator metric functions (e.g. `is_expected_tabs` from `desktop_env/evaluators/metrics`)
- [ ] @team — Make OSWorld-Human traces visible alongside OpenCUA traces in the viewer
- [ ] @team — Consolidate HTML annotation tool features (from Raghav's and Abdoul's versions); include: task ID, canonical task order, real task description, multiple ordered failure modes, large image on click, thinking trace (collapsed by default), action taken, side-by-side AI/human trace view, left-nav with category/prompt/step count, failing step field

## Open questions
- Should failure modes be prioritized by: step of occurrence, a custom prioritization function, or downstream impact (how many subsequent failures trace back to this one)?
- How should the taxonomy be updated given new observations?
- Does giving a VLM sequential screenshot history actually hurt performance — and if so, why?
- Can a frontier model achieve 100% success on OSWorld tasks when guided by OSWorld-Human notes? If not, why not?
- Is OSWorld still relevant given that frontier models are now evaluated on OSWorld v2.0?
- Is error analysis most valuable for small models only (since frontier models have few errors)?
- What is the lab-standard Bridges-2 setup for running vLLM with OpenCUA (conda env name, CUDA module, vLLM version)?
- Should OSWorld VMs run on AWS while inference stays on Bridges/Babel, or keep everything on the cluster?
- Has anyone already answered the core research question: "How much do successful trajectories improve automated CUA error analysis?"
