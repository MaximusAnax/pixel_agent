# Meeting notes — 2026-08-29

## Attendees
- Abdoul
- Raghav
- Amaad (referenced in notes)
- Matt (referenced in action items)

## Technologies discussed
- **Models:** UiTars-72B (grounding), OpenCUA-3B, OpenCUA-7B, Qwen3.5-VL 0.8B / 9B, Claude Sonnet 4.6 (judge)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, ScreenSpot V2, WebArena, VisualWebArena, ClawBench, A3/AITK, Mind2Web, WebLINX, AndroidWorld, VideoCUA/CUA-Suite
- **Clusters:** Babel (L40S GPUs), PSC Bridges-2 (Slurm), GPU-shared node v016
- **Frameworks:** vLLM (v0.11.0 confirmed working on Bridges with CUDA 12.6), BrowserGym
- **Datasets with human trajectories:** OSWorld-Human, WebArena (179 traces), VisualWebArena (233 traces), ClawBench, A3 (~3 trajectories/task), OmniGUI, VideoCUA, WebChain (31,725 traces), PC Agent-E (312 traces)
- **Key papers discussed:**
  - CUADebug [arXiv:2608.02643]
  - OSWorld-Human [arXiv:2506.16042]
  - Error analysis paper [arXiv:2606.31270]
  - How benchmarks mis-score [arXiv:2607.28367]
  - CUA-Suite [arXiv:2603.24440]
  - ClawBench [arXiv:2604.08523]
  - A3/AITK [arXiv:2501.01149]
  - OSWorld-G [arXiv:2505.13227]
  - Beyond the Final Answer (tool-augmented agent reasoning trajectories)

## Decisions made
- **vLLM version:** Use v0.11.0 on Bridges-2 with CUDA 12.6 module; v0.12.0+ and v0.23 are incompatible
- **Judge model:** Claude Sonnet 4.6
- **CUA models for traces:** OpenCUA-3B and OpenCUA-7B
- **Tier 1 benchmarks** for direct human↔agent comparison: OSWorld-Human, WebArena, VisualWebArena, ClawBench, A3
- **Keep all compute on Bridges/Babel** (do not split OSWorld VMs to AWS)
- **Cost threshold:** If frontier-model error analysis costs ~$25, proceed without checking in; if higher, consult Matt first
- **Judge design:** Ask judge to select *all* applicable failure modes (not primary/secondary only) given both agent and human trajectory
- **NeurIPS concurrent work policy noted:** Papers appearing after March 1, 2025 are considered concurrent; no comparison required (relevant to CUADebug)

## Feedback / critiques
- OSWorld-Human instructions are incomplete — e.g., instructions tell the model to type in a search bar but never to press Enter, causing human agent failures
- Model proceeds to next action while screen is still loading from prior action
- OSWorld initialization errors: initial environment sometimes not loaded properly (e.g., Chrome not opened on setup)
- UiTars-72B with OSWorld-Human as guide achieved only 60/361 tasks — many errors trace back to incomplete human steps
- Historical screenshots can confuse the model even when action history is included; unclear whether models are trained to understand sequential video frames

## Ideas considered
- **Oracle Agent:** Run OSWorld with a frontier model guided by OSWorld-Human notes to generate near-gold trajectories (target: 100% success rate); use these where true human trajectories are absent
- **Multi-path human trajectory analysis:** A3 has ~3 valid human trajectories per task, enabling strategy variation analysis
- **Image generation for grounding markup:** Use Stable Diffusion 3 or similar to mark up screenshots (e.g., houndstooth pattern) to aid click-target identification; use traditional CV to locate the generated marker
- **Reward efficient thinking:** Train/prompt CUAs to think concisely — penalize excessive reasoning steps relative to task complexity
- **Compressed GUI state as memory:** Rather than passing raw screenshots in context, learn a compressed GUI state representation to pass alongside last actions; could help with pop-ups/ads appearing unexpectedly
- **Two-model architecture:** Separate perception (grounding model) from planning (action model); optionally add a third model for tool calls (e.g., documentation lookup)
- **RL for action prediction:** Predict post-action state, then nudge model toward the best action; supervise reasoning traces
- **Instruction enhancement:** Use an LLM to expand the original task instruction with broad directions and success metrics before passing to the CUA
- **Learning from YouTube computer-use tutorials** (already partially addressed by CUA-Suite)
- **Auto-research / multi-agent spinning up literature review** (Karpathy-style; flagged as P3/later)

## Ideas & research directions
- **Primary direction — Error analysis paper:**
  - Goal: Reusable framework for CUA error analysis using gold/human trajectories; quantify how much gold trajectories improve automated error analysis and which trajectory properties drive that improvement
  - Compare judge (with gold trajectories) vs. judge (without gold trajectories) vs. human annotation; compute inter-annotator agreement across all pairs
  - Reference for analysis without gold traces: *Beyond the Final Answer* (tool-augmented agent reasoning)
- **Taxonomy refinement:** Consider prioritizing failure modes by (a) step of occurrence (earlier = more impactful), (b) downstream cascade impact, or (c) a custom prioritization function
- **Pilot inter-annotator study:** Raghav and Abdoul each manually annotate the same ~10 traces (single OpenCUA model); compute human1/human2, human1/judge, human2/judge agreement
- **Streaming visual observation direction:** Compressed memory / frame-difference summaries for tasks involving scrolling, video, or dynamic UIs — not yet solved for frontier models either
- **Small VLM CUA direction:** Investigate whether small models fail differently and whether harness design, imitation learning, or RL can close the gap without scaling

## Action items
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: human agent succeeded, OpenCUA-3B and 7B both failed, and judge already produced a failure-mode conclusion
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Read error analysis papers to survey existing failure taxonomies
- [ ] @Raghav — Finish gathering human trajectory screenshots from OSWorld-Human dataset via benchmark environment and merge into repo
- [ ] @Raghav — Find a method to transform OSWorld-Human instructions into more accurate/complete steps to increase human agent success rate (e.g., address missing "press Enter" steps)
- [ ] @Raghav — Investigate initialization bugs and hanging states in OSWorld (e.g., why Chrome is not opened on setup)
- [ ] @Abdoul — Start with pilot trajectories at path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- [ ] @Matt — Provide OpenAI API access to the team

## Open questions
- How should failure modes be prioritized — by step of occurrence, downstream impact, or a custom function?
- Should the taxonomy allow multiple failure modes per step (current direction: yes, select all that apply)?
- Is OSWorld still a relevant benchmark given that frontier models are evaluated on OSWorld v2.0 — is error analysis only meaningful for small models?
- Do CUAs perform worse when given screenshot history as context, and if so, why? Are any current VLMs actually trained on sequential video frames?
- Can a frontier model guided by OSWorld-Human notes achieve 100% success rate to serve as an oracle? If not, what are the blockers?
- What is the lab-standard conda env, CUDA module, and vLLM version for serving OpenCUA on Bridges/Babel?
- Has anyone already answered: *how much do gold trajectories improve automated CUA error analysis, and which trajectory properties matter most?*
