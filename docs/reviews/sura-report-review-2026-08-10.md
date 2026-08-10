# Review — `PixelAgent_Research.pdf` (SURA Report, 2026-08-03)

**Reviewer:** Claude · **Date:** 2026-08-10
**Intended repo location:** `docs/reviews/sura-report-review-2026-08-10.md`
**Reviewed against:** the Google Drive project folder (9 docs, incl. the rolling
meeting notes and the OSWorld-Human literature report), the `pixel_agent` repo
(`failureTaxonomy.md`, `failureAnalysisFinalPlan.md`, `failureStudyProtocol.md`),
and the SURA EOS Report (2026-07-30).

Status: **not yet addressed.** Tick items as they land.

---

## What works — keep these

- **The pivot narrative.** Framing the report around "benchmark noise forced us to
  build a verified evaluation pipeline before calibrating the judge" is honest,
  well-motivated, and more interesting than a clean result would have been. It is
  the report's spine.
- **Grounding reproduction as a validity check.** Reproducing published ScreenSpot
  V2 / OSWorld-G numbers on your own vLLM stack *before* attributing OSWorld
  failures is the step most people skip. It is also the only figure in the report,
  and its claim checks out against the raw numbers (see §1.6 below).
- **Taxonomy with a worked example per leaf.** Appendix B is genuinely useful —
  it is what makes the label set operational rather than decorative.
- **Related work that earns its place.** §3 connects each grounding paper to a
  *design decision* ("this is why perception/grounding is a separate branch")
  rather than listing citations. That is the right way to write related work.

---

## 1. Substantive — address before circulating further

### 1.1 The 60/361 result is framed as the wrong kind of experiment ⬜

**Where:** Abstract (lines ~12–14), Introduction, §5 Expected Outcomes.

The abstract reads: *"Our preliminary error analysis on a UI-TARS-72B rollout over
OSWorld (60/361 tasks succeeded)…"* — which reads as a standard agent rollout
measuring model capability.

Per the rolling meeting notes, it was not. UI-TARS-72B was the **grounding model
for an oracle/human-agent run** that replayed OSWorld-Human's human-validated steps
to generate a screenshot per human step. §4.1 states this correctly ("UI-TARS-72B
generates reference screenshots by following human trajectories"); the abstract,
intro, and §5 do not.

**Why it matters.** As a rollout, 60/361 is unremarkable — models fail OSWorld. As
a **ceiling experiment**, it is striking: a 72B model executing a known-correct
human solution scores 16.6%. That reframing turns the pivot from a judgment call
into a forced conclusion, and it is the strongest evidence the project has.

**Fix:** state the run's purpose in the abstract. Something like — *"An oracle run
that replays OSWorld-Human's validated human steps, which should approximate an
upper bound, succeeded on only 60/361 tasks."*

### 1.2 Related work omits the closest prior art ⬜

**Where:** §3.

Missing entirely: **AgentRewardBench**, **WebJudge / Online-Mind2Web**, **TRAIL**,
**AgentRx**, **AgentProcessBench**. These are the trajectory-judge calibration
papers a reviewer will benchmark this work against, and the first question will be
"how is this different from AgentRewardBench?"

The answer already exists. The team's own literature report (Drive, *Report on
OSWorld-Human and Human-Trajectory Benchmarks for Failure-Analysis Judge
Calibration*, 2026-07-03) surveyed all of them and concluded the gap is real:
human-trajectory datasets give you a correct path, judge benchmarks give you human
labels on bad trajectories, and **nothing joins the two in computer use**. That
paragraph belongs in §3.

Two findings from those papers also bear directly on the design and are worth a
sentence each:

- **AgentRewardBench**: judges **over-trust agent reasoning**. Our judge is given
  the agent's CoT → motivates a with/without-CoT ablation (§4 already lists this
  ablation; connect it to the citation).
- **WebJudge**: ~85% human agreement via key-point/key-screenshot selection;
  judges degrade with *both* too little and too much unfiltered evidence →
  supports feeding curated keyframes rather than whole traces.

**Also missing: OSWorld-Verified** is never cited, despite being the benchmark
named as the target throughout the planning docs and the one frontier labs report.

### 1.3 Appendix B is not the full taxonomy ⬜

**Where:** Appendix B / Table 2, and Table 1 in §5.2.

Appendix B is introduced as *"the full taxonomy … as used to prompt the judge and
to guide human annotators."* It lists 14 model-failure modes. `failureTaxonomy.md`
(frozen v1.0) has **16**. Missing:

- **Hidden Operation Blindness** — goal understood, agent tries only visible
  controls when ground truth needs a menu / shortcut / context menu / sidebar tab.
- **Cross-Application Context Loss** — state lost across an app switch.

**Why it matters.** `failureAnalysisFinalPlan.md`'s success criteria explicitly
require *"Hidden Operation Blindness rate reported for OSWorld"* and
*"Cross-Application Context Loss on `cross_app` tasks only."* A judge prompted from
Appendix B cannot produce either. And Hidden Operation Blindness is a plausible
explanation for a real share of the 301 failures — omitting it biases the label
distribution toward grounding modes, which is precisely the hypothesis §5 sets out
to test.

**Related:** the third category (benchmark/environment artifact) is a genuine
contribution but does not exist in `failureTaxonomy.md` at all — that file is
2 categories + the `evaluator_mismatch` / `propagated_failure` meta-labels.
Note `evaluator_mismatch` is *narrower* than what you found: it covers "reasonable
action, script says fail," not incomplete human-step instructions or VM init
failure.

**Fix:** pick one resolution and make one artifact authoritative —
(a) ratify the third category into `failureTaxonomy.md`, keeping all 16 model
leaves → 3 categories / 19 leaves; or (b) keep the frozen 16 and express benchmark
artifacts as two additional meta-labels. Option (a) matches how the team talks
about the problem now and makes the third category a *findable result*.
`failureTaxonomy.md` requires Abdoul's approval to change (root `AGENTS.md`).

### 1.4 Built and planned are not distinguished ⬜

**Where:** §4.1.

The pipeline is described in the present tense throughout, but per the meeting
notes: human-trajectory screenshots were still being gathered; OSWorld-Human is
**not yet folded into** the judge; and passing evaluator-function semantics to the
judge is still an agreed TODO, not a shipped feature.

For a SURA report this matters — the honest version is more credible, and the EOS
report already models the right tone. **Fix:** mark each of the three pipeline
components as built / in progress / planned, or add one sentence in §4.1 saying
what runs today.

### 1.5 The evaluation statistic is unnamed ⬜

**Where:** §2 (end), §4.1 (end).

- *"percent agreement and inter-rater reliability"* → `failureStudyProtocol.md`
  specifies **per-leaf Cohen's κ, target κ ≥ 0.6**, with 5+ anchor examples per leaf
  in the judge prompt, and 150–200 first-failure steps across two annotators.
  Name the statistic and the target.
- *"agreement between annotators on a pilot set of **n** traces"* — literal
  placeholder `n` left in the text.
- §5's expected outcomes are qualitative; the protocol promises prevalence with
  **confidence intervals**, a **co-occurrence matrix**, and **propagation rates**.
  Either promise those or say why they're out of scope for this report.

### 1.6 Figure 1's claim — verified, no change needed ✅

Checked against the raw numbers in the meeting doc:

| Benchmark | Scale | Published | Ours |
|---|---|---|---|
| ScreenSpot V2 (1,272) | 7B | 88.8 | 88.7 |
| OSWorld-G (564) | 7B | 31.4 | 34.8 |
| ScreenSpot V2 (1,272) | 32B | 87.0 | 91.5 |
| OSWorld-G (564) | 32B | 46.5 | 48.8 |

"Track the published figures closely, and exceed them on OSWorld-G at both scales"
is accurate. **One gap:** the *model family* behind the 7B/32B rows is not stated
anywhere — in the report or any source doc. Record it before publication.

---

## 2. Smaller corrections

- ⬜ **Broken cross-reference.** §4.1 (line ~141): *"a stretch goal rather than our
  core pipeline (Section 5.2)"* — §5.2 is the taxonomy table. The stretch goal is
  **§4.2**.
- ⬜ **369 vs 361.** §2 says OSWorld provides 369 tasks; the run reports 60/**361**.
  The 8-task gap is unexplained in every source. Explain or reconcile.
- ⬜ **Unsourced claim.** *"The current frontier models (Opus 4.8 onwards) pass the
  majority of these tasks"* — needs a citation or softening.
- ⬜ **No timeline.** §6 assigns ownership but gives no milestones, and §4.2
  references "the **Midway checkpoint**" without ever dating it.
- ⬜ **Typos.** Missing space in `models(Opus 4.8 onwards)`; `ie.` → `i.e.` (§2);
  run-together `e.g.is expected tabs` (§2); `evaluator function` formatting is
  inconsistent between §2 and Appendix A.

---

## 3. Optional — strengthens the contribution

- ⬜ **Use the `grouped-action` annotation explicitly.** OSWorld-Human ships both
  `single-action` and `grouped-action` human traces. The single-action view exposes
  unnecessary *motor-level* actions; the grouped view exposes unnecessary
  *cognition-level replanning* — which is what the cognitive/planning leaves are
  actually about. Saying which one the judge sees, and why, is a cheap
  methodological win.
- ⬜ **State that the judge is reference-guided, not reference-bound.** A model can
  deviate from the human path and still be correct; multiple valid trajectories
  exist. Committing to milestone coverage / recoverability / goal preservation
  rather than sequence matching pre-empts an obvious reviewer objection.
- ⬜ **Report the human-oracle ceiling as a headline number.** "OSWorld-Human
  replay achieves only 16.6% under a 72B grounding model" is a contribution in its
  own right, independent of the judge.
