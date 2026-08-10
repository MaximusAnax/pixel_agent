# PXA-022 — Deep-research prompt: does prior error analysis on other benchmarks undermine our novelty?

Paste everything below the line into a Cowork / deep-research session as-is.
It is self-contained — no repo access needed.

---

I'm doing research on computer-use agents (CUAs) at CMU. Our project builds an
**LLM judge that diagnoses *why* a CUA trajectory failed**, by comparing the
failed agent trajectory against a **validated human reference trajectory** for
the same task, classifying into an explicit failure-mode taxonomy
(perception/grounding vs. cognitive/planning leaves), and **calibrating the
judge against two independent human annotators** (per-leaf Cohen's κ) before
trusting its labels. We currently build on OSWorld + OSWorld-Human.

**The question I need answered:** Does existing error/failure analysis on
benchmarks *other than OSWorld* already do this — and if so, does it render our
contribution non-novel? I need a decisive survey, not a list of tangents.

## What we already know (do not re-derive; build on it)

From our July 2026 review of the OSWorld-Human citation graph:

- **OSWorld-Human** (arXiv 2506.16042) is used by later work only as an
  *efficiency* benchmark (WES metric). We found no paper using its human
  trajectories for failure diagnosis or judge calibration.
- The closest **judge/trajectory-analysis** line: AgentRewardBench (2504.08942),
  WebJudge / Online-Mind2Web (2504.01382), TRAIL (2505.08638), AgentRx
  (2602.02475), AgentProcessBench (2603.14465). These calibrate judges against
  **human labels of bad trajectories**, but none condition on a
  **human-optimal reference trajectory** for the same task.
- Human-demonstration datasets (Mind2Web, WebLINX, Android in the Wild,
  MolmoWeb human subset, PC Agent-E) use human traces for **training or
  replay**, not for reference-conditioned failure diagnosis.
- Sun et al. 2026, "Learning from Failure: Inference-Time Self-Improvement for
  Computer-Use Agents" shares our goal (structured value from failed traces)
  but does not condition on human references or calibrate against annotators.

So the specific claim to stress-test: **"reference-conditioned CUA failure
diagnosis with an annotator-calibrated judge does not yet exist."**

## What to search (be exhaustive on these, then expand)

For each benchmark, answer three things: (1) does it ship human reference
trajectories or gold action sequences? (2) has anyone published a
failure-mode/error analysis on it (paper section, workshop paper, or repo)?
(3) if yes, does that analysis condition on the human reference and/or
calibrate an automated judge against human annotators?

- **WebArena / VisualWebArena / WebArena-Verified** — we've heard WebArena may
  have human trajectories; confirm and check for error analyses.
- **TheAgentCompany** (arXiv 2412.14161)
- **OSWorld v2 / OSWorld-Verified** — including any frontier-lab error
  breakdowns published alongside results.
- **AndroidWorld / Android in the Wild / MobileAgentBench**
- **Mind2Web / Online-Mind2Web / Mind2Web 2**
- **GAIA, WebVoyager, WorkArena, AssistantBench, OfficeBench, Windows Agent
  Arena, ScienceAgentBench**
- **"How Do AI Agents Do Human Work?"** (arXiv 2510.22780) — compares AI and
  human workflows across occupations; check how deep the failure analysis goes
  and whether human workflows serve as diagnostic references.
- Any 2025–2026 survey of agent failure modes / agent evaluation that
  aggregates error analyses across benchmarks.

Also search the inverse direction: papers proposing **failure taxonomies for
GUI/web/computer-use agents** (not tied to one benchmark), and check what they
diagnose against and whether any calibrate vs. humans.

## Deliverable

1. **A table**: benchmark · human reference trajectories? (yes/no/partial) ·
   published error analysis? (citation) · reference-conditioned? ·
   judge-calibrated vs. humans? · how close to our design (0–3) · one-line note.
2. **A verdict paragraph**: is the novelty claim intact, threatened, or dead?
   If threatened, name the exact paper(s) and the precise delta that remains
   ours (e.g. "they diagnose but don't calibrate," "they calibrate but
   reference-free," "mobile-only").
3. **A "borrow list"**: anything these works do that we should adopt
   (metrics, taxonomy structure, annotation protocol).
4. Full citations with arXiv IDs/links for everything in the table.

Prioritize 2025–2026 work; flag anything published in the last 3 months
specifically. If you find a paper that appears to kill the novelty claim, stop
breadth-searching and go deep on that one paper instead.
