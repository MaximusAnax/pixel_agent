# Novelty scan — Failure/error analysis of small CUA models on OSWorld

> Answers the PROJECT_STATE action item "Read the space of other benchmarks
> (TheAgentCompany, WebArena, OSWorld-G) and determine whether existing error
> analysis renders our approach non-novel." Compiled 2026-08-10 by a Claude
> research agent (web search + GitHub raw reads; arxiv.org/HF direct fetches
> were blocked by the sandbox proxy, so items marked "(unverified from
> primary)" need re-checking against the PDFs before citing in a paper).

**Scope question:** Does existing error analysis on TheAgentCompany, WebArena,
or OSWorld-G (or anything else, 2024–Aug 2026) make pixelAgent's planned error
analysis (small open CUA models on OSWorld; VLM-as-judge with a
perception/grounding-vs-cognitive/planning multi-label taxonomy; human gold
labels; human–human and human–judge agreement; judge calibration loop)
non-novel?

## TL;DR verdict

The planned study is **not non-novel as a whole, but the field has moved fast
and two 2026 papers overlap substantially**: **CUADebug (arXiv 2608.02643)** —
a human-annotated OSWorld failure benchmark with a 2-level CUA error taxonomy —
and **"Naive Visual Memory is Not Enough" (arXiv 2606.14106)** — a 4-class
perception-vs-cognition failure taxonomy applied multi-label via LLM-judge on
OSWorld. Neither, however, does what pixelAgent plans as its core: a
**measurement-validity study** (human–human + human–judge agreement with a
calibration loop) of failure-mode labeling for **small open CUA models**
specifically. That slice is still open.

## 1. TheAgentCompany

**TheAgentCompany: Benchmarking LLM Agents on Consequential Real World Tasks**
— arXiv [2412.14161](https://arxiv.org/abs/2412.14161) (Dec 2024; NeurIPS 2025
D&B). 175 simulated-company tasks (GitLab, OwnCloud, Plane, RocketChat).

- **Error analysis done:** checkpoint-based partial credit; qualitative
  "common agent failures" discussion (*lack of social skills*, *incompetence
  in browsing*, *"deceiving oneself"* — fake shortcuts like renaming a chat
  user to impersonate a missing colleague).
- **Taxonomy/labels/agreement:** no formal taxonomy, no systematic human
  failure labels, **no inter-annotator agreement statistics found**.
- **Verdict:** qualitative, frontier agents, bespoke benchmark — **does not
  preempt the plan.**

## 2. WebArena lineage and web-agent failure studies

- **WebArena** — arXiv [2307.13854](https://arxiv.org/abs/2307.13854). Authors'
  failure analysis qualitative (observation/planning failures, loops,
  premature stopping). No taxonomy rigor, web not desktop.
- **WebSuite** — arXiv [2406.01623](https://arxiv.org/pdf/2406.01623) (Jun
  2024). Granular web-agent failure breakdown by action type; ability probes,
  not trajectory-level taxonomy with gold labels.
- **An Illusion of Progress? (Online-Mind2Web + WebJudge)** — arXiv
  [2504.01382](https://arxiv.org/abs/2504.01382) (Apr 2025). WebJudge
  (o4-mini) reaches **85.7% agreement with human success labels**; Operator
  failure analysis: 57.7% filter/sort errors. Judge validates binary success,
  not failure modes.
- **WebArena Verified** — [OpenReview](https://openreview.net/forum?id=94tlGxmqkN)
  (NeurIPS 2025 wksp). Benchmark repair + evaluator reliability (FN rate
  −11.3pp), not agent-error taxonomy.
- **AgentRewardBench** — arXiv [2504.08942](https://arxiv.org/abs/2504.08942)
  (Apr 2025). **1,302 trajectories**, expert labels (success, side effects,
  repetition), ~12 LLM judges evaluated. Closest judge-vs-human-gold
  methodology paper, but web-only, success labels not failure taxonomy,
  single annotator (no human–human agreement), no calibration loop.
- **WebVoyager** — arXiv [2401.13919](https://arxiv.org/abs/2401.13919).
  GPT-4V judge: **85.3% agreement, κ=0.70** (human–human κ≈0.70) (unverified
  from primary). Success-only.
- **Web-Shepherd** — arXiv [2505.15277](https://huggingface.co/papers/2505.15277)
  (NeurIPS 2025 Spotlight). Process reward model, 40K annotated checklists —
  training, not diagnosis.
- **When Web Agents Finish but Still Fail** — arXiv
  [2606.20724](https://arxiv.org/abs/2606.20724) (Jun 2026). Silent failures;
  judge-scored; no human-labeled taxonomy.
- **BrowserArena** — arXiv [2510.02418](https://arxiv.org/pdf/2510.02418).
  Step-level annotations, three narrow failure modes.

## 3. Grounding-focused error breakdowns

- **OSWorld-G / Jedi** — arXiv [2505.13227](https://arxiv.org/abs/2505.13227)
  (NeurIPS 2025 Spotlight). 564 grounding samples **broken down by capability
  type** (text matching, element recognition, layout, fine-grained
  manipulation); Jedi-3B/7B models. **Static single-step grounding benchmark**
  — dissects the perception half only, programmatic scoring, no trajectory
  labeling. Use it to independently measure grounding capability.
- **ScreenSpot-Pro** — arXiv [2504.07981](https://arxiv.org/abs/2504.07981)
  (ACM MM 2025). 1,581 expert pairs, 23 pro apps; per-app/category breakdowns.
  Grounding-only.
- **ScreenSpot-V2** (OS-Atlas) — arXiv [2410.23218](https://arxiv.org/abs/2410.23218).
  Fixed ~11.32% annotation errors in ScreenSpot. Dataset repair.
- **UGround / SeeAct-V** — arXiv [2410.05243](https://arxiv.org/abs/2410.05243)
  (ICLR 2025). **Manual error analysis of 60 sampled failures per split**
  attributing planning vs grounding; planning dominated. Direct ancestor of
  the perception-vs-cognition split, but small-sample, author-annotated (no
  IAA), no judge, not OSWorld desktop.

## 4. OSWorld family — status and 2026 relevance

- **OSWorld** — arXiv [2404.07972](https://arxiv.org/abs/2404.07972). Authors'
  qualitative analysis: mouse-click (grounding) inaccuracies dominant
  (~75%+ of GPT-4V failures; unverified from primary), env noise, missing
  domain knowledge.
- **OSWorld-Verified** — [XLANG blog 2025-07-28](https://xlang.ai/blog/osworld-verified).
  300+ task/evaluator fixes, AWS parallelization. **The version to use, with
  a pinned release.**
- **Validity critiques:** Agentic Benchmark Checklist — arXiv
  [2507.02825](https://arxiv.org/abs/2507.02825) — found **13/46 OSWorld
  Chrome tasks broken** by drift; "How Benchmarks Mis-Score Computer-Use
  Agents" — arXiv [2607.28367](https://arxiv.org/html/2607.28367v1) —
  scripted-oracle brittleness, drift, contamination.
- **OSWorld 2.0 exists** — arXiv [2606.29537](https://arxiv.org/abs/2606.29537)
  (Jun 2026; [repo](https://github.com/xlang-ai/OSWorld-V2)). 108 long-horizon
  workflows (~1.6h skilled-human median), 31 self-hosted sites, checkpoint
  partial credit (avg 27.25/task); no system exceeds ~21% end-to-end.
- **Still relevant for small models? Yes.** Frontier ~85% on Verified (near
  saturation → v2 built), but small open models are far from ceiling: per
  [OpenCUA](https://github.com/xlang-ai/OpenCUA) (arXiv
  [2508.09123](https://arxiv.org/abs/2508.09123)): **OpenCUA-7B 26.6%,
  UI-TARS-1.5-7B 27.4%, OpenCUA-32B 34.8%, OpenCUA-72B 45.0%, Qwen2.5-VL-7B/32B
  ≤5%**.
- **⚠ Correction for PROJECT_STATE: there is no "OpenCUA-3B".** The family is
  7B/32B/72B (Qwen2.5-VL-based). The 3B-scale siblings are **Jedi-3B**
  (grounding-only) and **Qwen2.5-VL-3B**. The plan's "OpenCUA-3B and 7B both
  failed" slice needs re-specifying (e.g. OpenCUA-7B + Qwen2.5-VL-3B, or
  7B/32B).

## 5. Closest prior art (read these first)

1. **CUADebug** — arXiv [2608.02643](https://arxiv.org/abs/2608.02643) (Aug
   2026). **Closest overlap.** Two-level CUA error taxonomy; **CUAErrorBench:
   204 human-annotated failed OSWorld trajectories** (root-cause step, L1/L2
   label, evidence, corrective strategy, confidence; L1 distribution: task
   reasoning & control 110/204, perception 36, grounding/interaction 25,
   external/system 13, other/infeasible 20); CUADebugger RCA agent (Gemini
   2.5 Pro: 11.2%→19.6% joint subtype+step accuracy; repair 12.2%→25.86%).
   **Annotator count / IAA not found — verify against PDF.** Single root
   cause, mainly a frontier Claude agent. pixelAgent **must cite, compare,
   and ideally reuse CUAErrorBench**.
2. **Naive Visual Memory is Not Enough** — arXiv
   [2606.14106](https://arxiv.org/abs/2606.14106) (Jun 2026). Four-class
   pipeline taxonomy (*cognitive failure*, *visual state misunderstanding*,
   *hidden operation blindness*, *grounding error*), **multi-label via
   Codex LLM-judge with evidence-visibility rule**, incl. OSWorld 316-task
   subset; memory design shifts failure distribution; AGMem +33.3%. **No
   human gold labels or judge–human agreement surfaced.** Remaining edge for
   pixelAgent: human-gold + dual agreement + calibration, small-model focus.
3. **Rethinking Inference-Time Scaling in Local CUAs** — arXiv
   [2607.28573](https://arxiv.org/html/2607.28573) (Jul 2026). Qwen3-VL-8B/
   30B-A3B, UI-TARS-1.5-7B, OpenCUA-7B on OSWorld; compute scaling changes
   failure modes. Exactly the model class, but heuristic-driven failure
   characterization; no gold labels/agreement.
4. **Model or Harness?** — arXiv [2607.28802](https://arxiv.org/abs/2607.28802)
   (Jul 2026). **41 failure modes** on interaction edges; **best LLM judge
   κ=0.76 vs human labels**. Generic agent traces, single-label; the standing
   "judge κ vs human on failure taxonomy" precedent to beat.
5. **OSWorld-Human** — arXiv [2506.16042](https://arxiv.org/abs/2506.16042)
   (MLSys 2026 oral). Human minimal-step trajectories for all 369 tasks;
   agents take 1.4–2.7× more steps; WES± metrics. Efficiency, not taxonomy.
6. **Learning from Failure: Inference-Time Self-Improvement** — arXiv
   [2606.31270](https://arxiv.org/abs/2606.31270). LLM diagnoses failures →
   patches; OpenCUA-72B 42.3→48.9%. Instrumental, unvalidated categories.
7. **GUI-RobustEval / RoTS** — arXiv [2605.29447](https://arxiv.org/html/2605.29447v1).
   1,216 injected policy-error test cases; error type + horizon. Synthetic
   errors for robustness training.
8. **GUI vs. CLI** — arXiv [2606.24551](https://arxiv.org/abs/2606.24551);
   **HiViG critic** — arXiv [2606.11078](https://arxiv.org/html/2606.11078);
   **GUI-Critic-R1** — arXiv [2506.04614](https://arxiv.org/abs/2506.04614);
   **Agent S/S2** — arXiv [2410.08164](https://arxiv.org/pdf/2410.08164),
   [2504.00906](https://arxiv.org/abs/2504.00906); **BacktrackAgent** — arXiv
   [2505.20660](https://arxiv.org/pdf/2505.20660); **Unintended Consequences
   (CHI 2026)** — arXiv [2505.09875](https://arxiv.org/abs/2505.09875); **How
   Do AI Agents Do Human Work?** — arXiv
   [2510.22780](https://arxiv.org/abs/2510.22780) (agents 32.5–49.5pp less
   successful; 93.8% programmatic solutions; documents data fabrication).

## 6. General agent failure taxonomies (methodological precedents)

- **MAST** — arXiv [2503.13657](https://arxiv.org/abs/2503.13657) (Berkeley).
  14 failure modes / 3 categories; ~150 expert-annotated traces; **human–human
  κ=0.88** after taxonomy iteration (initial κ≈0.24); **o1 annotator 94%
  acc / κ=0.77**. Multi-agent text systems — the methodological gold standard
  pixelAgent mirrors on CUA territory.
- **TRAIL** — arXiv [2505.08638](https://arxiv.org/abs/2505.08638). 148
  traces, 841 errors; best LLM ~**11%** joint localization — judge validity
  cannot be assumed.
- **AgentErrorTaxonomy / AgentDebug** — arXiv
  [2509.25370](https://arxiv.org/abs/2509.25370). 200 trajectories, 10 expert
  annotators, **κ=0.55** — a realism anchor for human agreement on failure
  labels.
- **Who&When** — arXiv [2505.00212](https://arxiv.org/abs/2505.00212);
  **Silent Failure** — arXiv [2606.09863](https://arxiv.org/abs/2606.09863)
  (no judge config exceeds AUROC 0.65 at false-success detection); **Deep
  Research errors** — arXiv [2606.02060](https://arxiv.org/abs/2606.02060).

## 7. Judge–human agreement precedents (calibration baselines)

| Work | Setting | Judge | Agreement vs humans |
|---|---|---|---|
| WebVoyager (2401.13919) | web success | GPT-4V | 85.3%, κ=0.70 (human–human κ≈0.70) |
| WebJudge (2504.01382) | web success | o4-mini | 85.7% |
| Agent-as-a-Judge (2410.10934) | DevAI requirements | agentic judge | 90.4–92.1% |
| MAST (2503.13657) | failure taxonomy (multi-agent) | o1 | 94% acc, κ=0.77 (human κ=0.88) |
| Model or Harness (2607.28802) | 41-mode taxonomy | frontier LLM | κ=0.76 |
| TRAIL (2505.08638) | fine-grained localization | Gemini-2.5-Pro | ~11% joint (near-failure) |
| Silent Failure (2606.09863) | false-success detection | 5 judges | AUROC ≤0.65 |
| CUADebugger (2608.02643) | CUA root-cause subtype+step | Gemini 2.5 Pro agent | 19.6% joint |

Pattern: judges near-human for **binary success**; moderate for **coarse
taxonomy** (κ≈0.76–0.77); poor for **fine localization / silent failures**.
Formal calibration loops are industry folklore, absent from CUA literature.

## 8. Verdict

**(a) Non-novel?** No single work preempts the plan, but three components are
individually claimed (taxonomy-on-OSWorld: CUADebug; perception-vs-cognition
multi-label judge on OSWorld: 2606.14106; small-local-CUA failure modes:
2607.28573). **Unclaimed as of 2026-08-10:** a reliability-first study that
(i) collects human gold labels **with reported human–human agreement** on a
CUA failure taxonomy, (ii) validates a VLM judge **per failure category**
against them, (iii) runs a **reported judge-calibration loop** with held-out
agreement, and (iv) compares **multi-label error profiles across small open
models**.

**(b) Gaps pixelAgent can own**

1. Human–human agreement for CUA failure labels on OSWorld (per-category κ /
   Krippendorff's α for multi-label) — a first.
2. Per-category judge validity for perception vs cognitive errors **with
   screenshots** against human gold.
3. Comparative multi-label error profiles of small open models at matched
   step budgets on OSWorld-Verified.
4. **Causal validation** of the perception-vs-planning split via
   interventions (oracle grounding / Jedi substitution) on OSWorld desktop
   trajectories.
5. A formalized, reported judge-calibration loop (what `autoResearch/` now
   implements).

**(c) Recommendations**

1. **Reposition around measurement validity, not taxonomy existence.** Adopt/
   map to CUADebug L1/L2 and 2606.14106's four classes — don't introduce an
   unmapped fourth taxonomy.
2. Run on **OSWorld-Verified with a pinned release**; cite the ABC and
   Mis-Score critiques; treat OSWorld 2.0 as a long-horizon contrast only.
3. **Fix the model list: no OpenCUA-3B exists.** Use OpenCUA-7B (+32B),
   Qwen2.5-VL-3B/7B or Qwen3-VL small, UI-TARS-1.5-7B; 3-run means; matched
   step budgets; pair with OSWorld-G/ScreenSpot-Pro grounding scores.
4. **Add an intervention arm** (oracle/Jedi grounding on a subsample) to make
   the perception-vs-cognition attribution causal — cheapest leapfrog over
   CUADebug and 2606.14106.
5. Target beating κ=0.76–0.77 (Model-or-Harness, MAST) per category; include
   silent-failure cases; **pull and read the CUADebug PDF before submission**
   (its IAA details could not be verified from this sandbox).
