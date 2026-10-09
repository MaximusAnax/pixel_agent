# Meeting notes — 2026-10-09

## Attendees
- Raghav, Abdoul (confirmed from Raghav + Abdoul tab for this session)

## Technologies discussed
- OSWorld-Human dataset ([arxiv 2506.16042](https://arxiv.org/abs/2506.16042))
- UITARS-72B (grounding model; 60/361 task success rate on OSWorld)
- OpenCUA-3B, OpenCUA-7B
- Sonnet-4.6 (LLM-as-judge)
- vLLM (v0.11.0 confirmed working on PSC Bridges-2 with CUDA 12.6)
- Babel cluster (L40S GPUs), PSC Bridges-2
- HTML annotation/viewer tool (combined Abdoul + Raghav viewers)

## Decisions made
- Use OSWorld-Human dataset as the guide for generating gold trajectories via a frontier model ("human agent")
- Use UITARS-72B as the grounding model for OSWorld runs
- Pilot trajectory set for taxonomy discovery located at: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- Judge should receive both human trajectory screenshots and model trajectory screenshots per step
- Prioritization of failure modes is an open design question (not yet decided)

## Feedback / critiques
- Human annotators and LLM judge can disagree on error type: one case where the referential expression for what to click was incorrect but model clicked correctly — judge labelled it "reasoning" error, human labelled it "grounding" error
- OSWorld-Human has incomplete human steps (e.g., instructions say type in search bar but never say press Enter), causing human agent failures
- Model sometimes moves to the next action while the screen is still loading from the previous action
- OSWorld initialization errors: initial environment not loaded properly (e.g., Chrome not opened on setup)
- Human agent achieved only 60/361 tasks — gold label creation is blocked by the above issues

## Ideas considered
- Prioritize failure modes by: (a) step of occurrence (earlier = more important), (b) a custom prioritization function, or (c) downstream impact (how many subsequent failures trace back to this one)
- Update/refine the existing error taxonomy based on findings from failure analysis papers

## Ideas & research directions
*(No new directions introduced in this session; carried from prior weeks)*

## Action items
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset and merge into repo
- [ ] @Raghav — Find a method of transforming human trajectories into more accurate instructions that lead to higher human-agent success rate
- [ ] @Raghav — Investigate and fix initialization bugs / OSWorld benchmark issues causing hanging states (e.g., Chrome not opened on setup)
- [ ] @Abdoul — Improve judge calibration based on gold labels for 5 specific tasks meeting criteria: (1) human agent succeeded, (2) OpenCUA-7B and 3B both failed, (3) judge made a conclusion on failure modes and steps
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in each trace
- [ ] @Abdoul — Read further into failure analysis papers to identify existing ways of categorizing failures

## Open questions
- How should failure modes be prioritized — by step of occurrence, downstream impact, or a custom function?
- Should the taxonomy be updated, and if so, how?
- What is the best method to transform incomplete OSWorld-Human instructions into reliable gold trajectories that achieve ~100% success rate?
