# Meeting notes — 2026-10-02

## Attendees
- Raghav
- Abdoul

## Technologies discussed
- OSWorld-Human dataset (human trajectory screenshots)
- HTML annotation/viewer tooling (Abdoul editing judge + HTML logic)
- LLM-as-a-judge (judge logic refinement)
- OpenCUA (3B and 7B)

## Decisions made
- Start pilot annotation with the existing paired taxonomy CSV before scaling up:
  - Path: `errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv`
- Refine judge logic to incorporate **both** human and model screenshots per step in the trace (not just model screenshots)

## Ideas considered
- Failure-mode prioritization strategies under consideration (not yet decided):
  - By step of occurrence (earlier failure = higher importance)
  - By a custom prioritization function (to be designed)
  - By downstream impact (how many subsequent failures trace back to this one)
- Updating the error taxonomy based on new observations from human trajectory data

## Action items
- [ ] @Raghav — Finish gathering screenshots of human trajectories from OSWorld-Human dataset via the benchmark environment, then merge into repo
- [ ] @Abdoul — Refine judge logic to incorporate both human and model screenshots per step in the trace
- [ ] @Abdoul — Continue editing HTML viewer to surface judge assessments alongside paired trajectories
- [ ] @Raghav, @Abdoul — Read failure analysis papers to survey existing failure categorization schemes and inform taxonomy updates

## Open questions
- How should the error taxonomy be updated given what is being observed in OSWorld-Human trajectories?
- Which failure-mode prioritization strategy is most appropriate: step order, downstream impact, or a custom function?
