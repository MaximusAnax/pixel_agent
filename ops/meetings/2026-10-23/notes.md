# Meeting notes — 2026-10-23

## Attendees
- Raghav
- Abdoul
- Amaad
- Matt (mentioned, not confirmed present)

## Technologies discussed
- **Models:** OpenCUA-3B, OpenCUA-7B, UiTars-72B, Qwen3.5-VL (0.8B, 9B), Claude Sonnet 4.6, GPT (Luna variant), Qwen 7B (offline judge), Opus 5
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, WebArena, VisualWebArena, ClawBench, A3/AITK, ScreenSpot V2
- **Infrastructure:** Babel (L40S GPUs), PSC Bridges-2, Slurm, vLLM v0.11.0
- **Frameworks/Tools:** OpenCUA harness, Playwright traces, HuggingFace datasets, BrowserGym
- **Repos of note:**
  - https://github.com/raghav3003/pixel_agent/blob/goldjudge-stage/
  - https://github.com/xlang-ai/OSWorld
  - https://github.com/WukLab/osworld-human

## Decisions made
- Use **3 judges**: Claude, GPT-Luna, offline Qwen-7B
- Use **Babel for L40S GPU** inference; keep OSWorld VMs on Bridges/Babel (not split across AWS)
- **vLLM v0.11.0** is the confirmed working version on Bridges-2 (CUDA 12.6)
- Bring a new person into the project — **yes, proceed**
- Error analysis should provide the judge with: reference trajectory, predicted trajectory, OSWorld metric score, and evaluator function definitions (e.g., `is_expected_tabs`)
- Judge should **select all applicable failure modes** (not just primary/secondary)
- Pilot annotation set: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- Abdoul and Raghav will **both manually annotate the same ~10 traces** to compute inter-annotator agreement (human/human, human/judge)

## Feedback / critiques
- Human annotators can be wrong: one case where referential expression was incorrect but model clicked correctly — human called it a "grounding" error; LLM judge called it a "reasoning" error
- OSWorld-Human instructions are incomplete in places (e.g., instructs model to type in search bar but never says to press Enter), causing gold trajectory failures
- Model sometimes moves to next action while screen is still loading from prior action
- OSWorld environment initialization errors (e.g., Chrome not opened on setup) cause hanging states
- UiTars-72B on OSWorld-Human guidance achieved only **60/361 tasks** — many errors attributable to environment issues rather than model failures
- Frontier models already achieve high OSWorld scores — raises question of whether OSWorld error analysis is still relevant for frontier models vs. only small models

## Ideas considered
- **Multi-subagent exploration:** Dispatch subagents to explore different UI paths simultaneously (e.g., each clicks a different tab); store exploration in vector/text DB for future reuse within the same UI. Analogous to coding agents exploring a large codebase, but materially different due to side effects of UI interaction.
- **Multiple Chrome instances** to isolate side effects during parallel exploration
- **Oracle Agent:** Run in OpenCUA to replay human actions and generate screenshots for every step
- **Screenshot generation for grounding:** Use image diffusion model (e.g., Stable Diffusion 3) to mark up GUI screenshots; use unusual patterns (e.g., houndstooth) as click targets detectable via traditional CV
- **Compressed GUI state as memory** instead of raw screenshots to handle pop-ups/ads and long-horizon context confusion
- **Dual-model architecture:** Separate perception model (grounding/bounding boxes) from planning model; optionally a third model for tool calls (e.g., web search for documentation)
- **Instruction enhancement via LLM:** Pre-process task instructions to add broad directions and success metrics before giving to the CUA
- **RL with predicted next-state supervision:** Teach model to predict state after candidate actions; supervise reasoning traces
- **YouTube tutorial data** for computer-use training (see: *Learning from Online Videos at Inference Time for Computer-Use Agents*)
- **Reward efficient thinking** to reduce unnecessary steps in planning/reflection phases
- **Auto-research agents** (Karpathy-style) spinning up subagents on a problem

## Ideas & research directions
- **Primary research question:** How much do gold/human trajectories improve automated LLM-as-a-judge error analysis of a CUA? What properties of those trajectories drive the improvement?
- **Comparison baseline:** *Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents* — error analysis without golden traces
- **Oracle/gold trajectory generation for OSWorld:** Provide OSWorld-Human notes to a frontier model to generate 100%-success-rate gold trajectories where true human traces are absent
- **CUADebug** [arXiv:2608.02643] — closely related; novelty of our work relative to it is the use of human trajectories
- **Tier 1 benchmark targets for human ↔ agent comparison:** OSWorld-Human, WebArena (179 human Playwright traces), VisualWebArena (233 human Playwright traces), ClawBench, A3/AITK
- **Failure mode prioritization function** to be designed: options include step of occurrence (earlier = higher weight), downstream impact (causal chain), or explicit priority ranking

## Action items
- [ ] @Raghav — Finish gathering screenshots of OSWorld-Human trajectories and merge into repo
- [ ] @Raghav — Find method to transform OSWorld-Human notes into more accurate step-by-step instructions that improve Oracle Agent success rate
- [ ] @Raghav — Investigate OSWorld initialization bugs causing hanging states (e.g., Chrome not opening on setup)
- [ ] @Raghav — Manually annotate the pilot set of ~10 traces (same set as Abdoul)
- [ ] @Abdoul — Improve judge calibration using gold labels for 5 tasks where: human agent succeeded, both OpenCUA-3B and 7B failed, and judge produced a failure-mode conclusion
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Manually annotate the pilot set of ~10 traces (same set as Raghav); compute inter-annotator agreement (human/human, human/judge)
- [ ] @Abdoul — Read failure analysis papers to survey existing failure categorization schemes; determine whether existing error analysis on non-OSWorld benchmarks renders our contribution non-novel
- [ ] @Amaad — For each Tier 1 benchmark, determine exactly what exists in the human trajectories (real browser actions vs. notes) and extent to which modern CUA work still uses that benchmark
- [ ] @Matt — Provide OpenAI API access to the team

## Open questions
- How should failure modes be prioritized — by step of occurrence, downstream causal impact, or a custom function?
- Should the taxonomy be updated, and if so, how?
- Is OSWorld still a relevant benchmark given that frontier models fail infrequently — is this analysis only useful for small models?
- Is there any prior work that has already answered: "How much do gold trajectories improve automated CUA error analysis?"
- What is the lab-standard conda env name, CUDA module, and vLLM version for running inference on Bridges-2?
- Why is Chrome not opened on OSWorld environment setup (initialization bug)?
- Do CUAs perform worse when given screenshot history as context, and if so, why? Are any current VLMs trained to understand sequences of frames?
