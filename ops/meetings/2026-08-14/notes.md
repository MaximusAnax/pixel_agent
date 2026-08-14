# Meeting notes — 2026-08-14

## Attendees
- Raghav, Abdoul (confirmed present for 2026-08-14 session)

## Technologies discussed
- **Models:** UITARS-72B (grounding model), OpenCUA-3B, OpenCUA-7B, Sonnet 4.6 (judge), Qwen3.5-VL 0.8B / 9B, frontier models (Opus 5)
- **Benchmarks:** OSWorld, OSWorld-Human, OSWorld-G, OSWorld-Verified, ScreenSpot V2
- **Datasets:** OSWorld-Human trajectories (`WukLab/osworld-human`), WebArena / VisualWebArena human trajectories (Playwright traces)
- **Infrastructure:** Babel (L40S GPUs), PSC Bridges-2, Slurm, vLLM 0.11.0 (CUDA 12.6 compatible)
- **Frameworks:** OpenCUA (`xlang-ai/OpenCUA`), BrowserGym
- **Papers referenced:**
  - CUADebug `arXiv:2608.02643`
  - OSWorld-Human `arXiv:2506.16042`
  - Error analysis paper `arXiv:2606.31270`
  - *Beyond the Final Answer* (tool-augmented agent reasoning trajectories)

## Decisions made
- Use **UITARS-72B** as grounding model for OSWorld runs; current success rate: **60/361 tasks**
- Use **Sonnet 4.6** as the LLM judge over OpenCUA-3B and OpenCUA-7B traces
- OSWorld-Human is **not yet folded in** to the judge pipeline — adding it is the next priority
- vLLM version standardized to **0.11.0** on Bridges (CUDA 12.6); do not use vLLM 0.23 (requires CUDA 13)
- Keep all compute (OSWorld VMs + inference) on Bridges/Babel rather than splitting across AWS
- Judge should receive: task description JSON + relevant evaluator metric functions (e.g., `is_expected_tabs` source from OSWorld evaluators repo)
- Error prioritization to be explored along three axes: step of occurrence, downstream impact, and a to-be-designed prioritization function

## Feedback / critiques
- OSWorld-Human instructions are **incomplete** in places (e.g., instruct model to type in search bar but never press Enter), causing human-agent failures
- Model proceeds to next action while screen is still loading from the previous step
- OSWorld environment has **initialization bugs** (e.g., Chrome not opened on setup) leading to hanging states
- NeurIPS concurrent-work policy: papers appearing after March 1 2025 (including CUADebug) are considered concurrent; comparison not required

## Ideas considered
- Ask judge to select **all applicable failure modes** from taxonomy (rather than primary/secondary only) when given both agent and human trajectories
- Transform OSWorld-Human human notes into accurate step-by-step instructions via a frontier model to raise human-agent success rate toward 100%
- Generate "Oracle Agent" trajectories: replay human actions in OpenCUA environment to produce a screenshot per step, usable as gold reference
- Failure mode prioritization function weighting: earlier occurrence → higher importance; downstream failure count as impact signal

## Ideas & research directions
- **Human vs. judge error analysis study:** have Raghav and Abdoul each independently annotate the same failure set, then compute inter-annotator agreement across three pairs: (human A / human B), (human A / judge), (human B / judge)
- **Gold trajectory generation:** where only human notes exist (OSWorld-Human), prompt a frontier model with those notes during live task execution; target 100% success rate as gold standard
- **Cost-gated frontier judge:** after trajectory collection, estimate input/output token cost for frontier model error analysis; proceed without approval if ≤ ~$25

## Action items
- [ ] @Abdoul — Improve judge calibration on 5 pilot tasks meeting criteria: human-agent succeeded, OpenCUA-3B and -7B both failed, judge produced a failure-mode conclusion
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Continue reading failure analysis papers for taxonomy categorization approaches
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo
- [ ] @Raghav — Find a method to transform human OSWorld-Human notes into more accurate step-by-step instructions to raise human-agent success rate
- [ ] @Raghav — Investigate and document OSWorld initialization bugs causing hanging states (e.g., Chrome not opening on setup)
- [ ] @Matt — Provide OpenAI API access to team

## Open questions
- Why is Chrome not opened on setup in OSWorld initialization? What other environment initialization bugs exist?
- Do incomplete human steps in OSWorld-Human systematically skew success/failure rates, and how should they be handled?
- How should the failure taxonomy be updated — and should prioritization weight step-of-occurrence, downstream impact, or a custom function?
- Is OSWorld still a relevant benchmark for frontier models, or is it now primarily useful for evaluating smaller models?
- Has anyone already answered: *how much do successful (gold) trajectories improve automated error analysis, and what trajectory properties drive that improvement?*
