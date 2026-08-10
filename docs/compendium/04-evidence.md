# 4 — Evidence

Every empirical number the project has, with provenance and what it does and does
not license you to say. **Ours** = produced by this team. **External** = read from
a paper or model card.

---

## OURS — the headline result

### UI-TARS-72B, OSWorld run guided by OSWorld-Human: **60 / 361 tasks succeeded**

*Source: rolling meeting notes doc, most recent full-team section.*

Read this carefully, because it is easy to misread and the report currently does.

This was **not** a standard agent rollout measuring OpenCUA capability. UI-TARS-72B
was used as the **grounding model for an oracle/human-agent run**: it followed
OSWorld-Human's human-validated steps, in order, to produce a screenshot for every
human step. The run was supposed to approximate a **ceiling** — a large model
executing a known-correct human solution should approach 100%.

It got **16.6%**.

That is the strongest evidence the project has produced, and it is evidence about
the *benchmark*, not the model. The failures that blocked gold-label creation were:

- **incomplete human-step instructions** in OSWorld-Human — e.g. instructions tell
  the agent to type into a search bar but never say to press Enter
- **premature next-action execution** — the model moves on while the screen is
  still loading from the previous action
- **OSWorld VM initialization failure** — the initial environment never finished
  loading (e.g. Chrome not open on setup)

**What this licenses:** the claim that a non-trivial share of raw OSWorld failures
are benchmark/environment artifacts, and therefore that calibrating a judge on
unfixed data would teach it to explain bugs as reasoning errors. This is the
justification for the whole "verify the pipeline first" pivot.

**What it does not license:** any claim about OpenCUA, small-model capability, or
failure-mode prevalence. It is one run, one grounding model, no seeds.

**Open discrepancy:** OSWorld has **369** tasks; this run reports **361** — and so
does the `opencua_a3b_pilot30` episode inventory. The same 361 appearing in two
independent places suggests a systematic exclusion (8 tasks dropped somewhere in
the HF packaging or inventory step) rather than a typo. Worth resolving before
publishing either number, and worth checking whether the dropped 8 are dropped for
a reason that matters.

---

## OURS — grounding reproduction (serving-stack validation)

*Owner: Raghav. Source: rolling meeting notes doc. Purpose: confirm that observed
OSWorld failures are not artifacts of our own vLLM serving.*

| Benchmark | Scale | Published | Ours |
|---|---|---|---|
| ScreenSpot V2 (1,272 samples) | 7B | 88.8 | 88.7 |
| OSWorld-G (564 samples) | 7B | 31.4 | **34.8** |
| ScreenSpot V2 (1,272 samples) | 32B | 87.0 | **91.5** |
| OSWorld-G (564 samples) | 32B | 46.5 | **48.8** |

Reproduced numbers track published figures closely and exceed them on OSWorld-G at
both scales. **This is a clean, load-bearing result**: it is what lets the project
attribute OSWorld failures to the agent or the benchmark rather than to a
misconfigured server. It is also the only result in the SURA report with a figure.

Caveat: the model family behind these rows is not recorded in any source available
here. Record it before publication.

---

## OURS — pilot labeling status (provisional)

*Source: `ops/state/PROJECT_STATE.md` @ 2026-07-10 and `ops/reports/2026-W26.md`.*

- Experiment group **`opencua_a3b_pilot30`** covers **361 inventoried episodes**.
- **16** labeled by the Claude Sonnet 4.6 judge, queued for human review.
  Judge cost: **$0.26** — comfortably inside the $25 gate.
- **Zero adapter gaps** on the OpenCUA A3B package, up from 1 the prior week.
- Provisional signal: **Reasoning Drift + Goal Hallucination together account for
  75% of the 16 labeled episodes.**
- **16/361 = 4.4% labeled.** Named in the weekly report as *the* key blocker;
  throughput scaling is the immediate next milestone before anything here can be
  called representative.

> ⚠️ **These are provisional judge labels, not gold.** Per the 2026-07-10 freeze,
> `judge_context_version`-tagged labels are reference during discovery only.
> The 75% figure is over **16 episodes** and has not been checked against a single
> human label. Do not put it in a paper, a slide, or a status update without the
> word "provisional" attached. It is also exactly the kind of early signal that
> tends to move once benchmark-artifact failures are separated out.

Paired pilot packet for discovery labeling — `pilot_taxonomy_paired_20260703`:
30 tasks × 2 models = 60 traces, from runs `20260626_172919_a3b_pilot_full_v4` and
`20260626_172922_7b_pilot_full_v4`.

Stale plumbing artifacts, **do not quote**: `errorAnalysis/data/prevalence.json`
(computed over `n_failures: 1`; every prevalence is 0.0 or 1.0 with CIs spanning
nearly the unit interval) and `errorAnalysis/data/attributions.jsonl` (1 line).

---

## EXTERNAL — the stat that shaped the project

**Icon grounding accuracy spans ~21–72% across models; text grounding is
comparatively saturated at ~70–82%.**

*Attributed to Amaad, drawing on the Qwen3-VL technical report; recorded in the
meeting notes doc (dated 2026-02-27 in the doc).*

This is the single observation that convinced the team that **grounding, not
planning, is the small-model bottleneck** — and it is why the taxonomy keeps
perception/grounding as a separate top-level branch from planning, and why
icon/software-commonsense recognition is broken out as its own leaf.

## EXTERNAL — model scores

Qwen3.5 model cards:

| | Qwen3.5-9B | Qwen3.5-4B |
|---|---|---|
| ScreenSpot Pro | 65.2 | 60.3 |
| OSWorld-Verified | 41.8 | 35.6 |
| AndroidWorld | 57.8 | 58.6 |

Qwen3.5-0.8B's card does **not** report OSWorld or comparable agentic numbers —
which is itself informative about what "small" costs.

## EXTERNAL — grounding fragility

- **GUI-Perturbed** (arXiv 2604.14262): models scoring **above 85%** on standard
  grounding benchmarks lose **27–56 points** under relational instructions or a
  simple 70% zoom. Direct evidence that static grounding accuracy overstates real
  robustness — and part of why benchmark/environment artifacts are treated as a
  category rather than folded into model failure.
- **ScreenSpot-Pro**: on high-resolution professional software, the best model of
  any size (at time of writing) solved **under 19%** of instructions. Grounding
  failure is not solely a small-model problem, though small models make it worse.

## EXTERNAL — OSWorld-Human

*From the OSWorld-Human paper (arXiv 2506.16042) and project post, via our own
literature report.*

- Covers all **369** OSWorld tasks across **9** applications. Human trajectories
  were built by manually performing every task, mapping into the OSWorld action
  space, cross-validating between two graduate annotators, and replaying inside
  the OSWorld VM to confirm the evaluator passes.
- Each task JSON carries a `human-ground-truth` object with **two parallel
  annotations**: `single-action` (flat atomic sequence) and `grouped-action`
  (groups executable from one observation without an intervening screenshot).
- Metric is the **Weighted Efficiency Score** — `WES+` rewards successes using
  fewer steps than the human reference; `WES-` penalizes failures in proportion to
  budget consumed. Split this way so a fast failure does not outrank a slow success.
- Agent S2 + Gemini 2.5 leads at **28.2** single-action WES+ / **17.4** grouped
  WES+, against **41.4%** on plain OSWorld success. Top agents take roughly
  **1.4×–2.7×** as many steps as necessary.
- For Agent S2, **planning and reflection LLM calls account for ~75–94% of total
  task time.**

> The `grouped-action` annotation is the more useful one for us. The `single-action`
> view exposes unnecessary motor-level actions; the `grouped-action` view exposes
> unnecessary *cognition-level replanning* — which is the thing our
> cognitive/planning leaves are about.

## EXTERNAL — judge-calibration literature

*From our own OSWorld-Human literature report (2026-07-03). Full detail in
[`05-literature.md`](05-literature.md).*

- **WebJudge / Online-Mind2Web**: ~85% agreement with human judgment by selecting
  key points and key screenshots before judging. Judges degrade with both too
  little evidence and too much unfiltered evidence.
- **TRAIL**: on human-annotated traces with a fine-grained error taxonomy, the best
  model reaches only **11% joint accuracy**. Trace debugging is genuinely hard and
  taxonomy design matters enormously.
- **AgentProcessBench**: 1,000 trajectories, 8,509 step labels (+1 / 0 / −1).
  Models struggle most on the **neutral vs. incorrect** boundary.
- **AgentRewardBench**: simpler trajectory representations can outperform richer
  ones; judges miss nuanced issues and **over-trust agent reasoning**.

> That last finding is a direct risk to our design: our judge is given the agent's
> chain-of-thought. Plan an ablation with CoT withheld.

## EXTERNAL — mitigation results worth knowing

- **RegionFocus** (visual test-time scaling): zoom into a salient sub-region after
  an error is detected. Reported to let a **7B model surpass a 72B model** on
  grounding.
- **Image-as-Map**: encode interaction history visually (e.g. pink stars on the
  screenshot) rather than as textual coordinates — reported to reduce action
  looping and help disambiguate nearby elements.
- **Memory Inception**: KV-cache footprint reduced **6.4×–118×** vs. visible
  prompting; latent banks stay effective past 24+ turns where visible prompts
  decay; no meaningful capability degradation on GSM8K/MMLU.
- **Instruction clarification**: rewriting vague instructions to make success
  criteria explicit has moved success **from 0% to 100%** in some reported
  scenarios. Directly relevant — this is exactly the OSWorld-Human
  incomplete-instruction problem, and suggests the fix is tractable.
- **PC Agent-E**: 312 human trajectories + reconstructed thoughts + per-step
  alternative actions → **141% relative improvement** over its base model.
- **AdaptAgent**: 1–2 human demonstrations → 3.36–7.21 absolute success points on
  unseen sites.

## Task-difficulty rule of thumb

Used throughout team discussion: **easy 3–4 steps, medium 4–9, hard 10+.**
Planning and reflection phases often consume far more steps than required,
especially on medium and hard tasks.

## Targets on record

From the Research Ideation Tracker:

| Metric | Baseline | Target | Source |
|---|---|---|---|
| Success rate, Ubuntu (pure visual) | 5.26% | > 15% | OSWorld-Verified |
| GUI grounding accuracy | low (pixel-level) | human-competitive | ScreenSpot-Pro |
| Inference latency | — | < 500 ms / action | edge/laptop hardware |

These are aspirational targets set at ideation time, not measured commitments.
