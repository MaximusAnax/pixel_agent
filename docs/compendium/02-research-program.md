# 2 — The research program

## Thesis

Benchmarks like OSWorld report one bit per task: pass or fail. That bit does not
say whether the agent mis-clicked a button, lost the plan, or was defeated by a
broken task setup. This project builds and eventually **calibrates** an
LLM-as-judge that classifies CUA failures against an explicit taxonomy, reasoning
over context the standard protocol throws away: the failed trajectory, the task
specification *and its evaluator semantics*, and a human reference trajectory.

The downstream purpose: once the judge is trustworthy, it points small-model CUA
improvement work at failure modes that are *real*, rather than at whatever an
uncalibrated label distribution happens to show.

## Current milestone — annotation-ready infrastructure

Set at the 2026-07-10 Phase 0 freeze. Read this before assuming any calibration
work is in flight.

> **Annotation-ready infrastructure**: OSWorld task/eval context vendored, Human
> Agent screenshots for annotators *and* the multimodal judge, mockup-approved
> dual-trace review UI, provisional rejudge `osworld_v1`. **Not** judge
> calibration, prevalence CIs, or paper figures.

The sequence from here:

| Stage | End-state |
|---|---|
| **Annotation-ready** *(current)* | Pilot review packet with OSWorld context, dual-trace UI, Human Agent screenshots, provisional `osworld_v1` labels |
| **Discovery labeling** | `abdoul` + `raghav` produce human labels on the pilot packet |
| **Phase D validation** | Gold-set κ; judge calibrated against gold; prevalence CIs for publication |

### The three-tier label model

The single most important distinction in the current phase:

| Role | Artifact | Status |
|---|---|---|
| **Provisional judge** | versioned labels (`judge_context_version`, e.g. `osworld_v1`) in packet / run outputs | reference during discovery; **not** scientific gold |
| **Human gold** | `annotations.json` from annotators `abdoul` / `raghav` | gold-in-progress → adjudicated gold |
| **Calibrated judge** | follow-on rejudge (e.g. `osworld_v2_gold_calibrated`) | used for scaled prevalence |

Provisional multimodal rejudge (`osworld_v1`) runs **after** Human Agent
screenshots are ready and **before** the discovery labeling batch. Never overwrite
prior judge outputs — version them.

### Human reference is non-binding

Formally decided 2026-07-10, and encoded in both `failureStudyProtocol.md` and
`failureTaxonomy.md`:

> The human sequence is **one viable path**, not the only valid path. Do **not**
> require step-wise alignment to the agent trace, and do **not** penalize agent
> actions that diverge from the human path if they still progress toward OSWorld
> success criteria. Prefer labeling agent failure modes over "didn't match human."

This resolves what the judge-calibration literature flags as the central risk of
reference-guided judging (see [`05-literature.md`](05-literature.md)). It also
means the SURA report's framing — the judge diagnosing *against* the reference —
needs softening to "reference-guided, not reference-bound."

## The two-level task

**Level 1 — the CUA task.** Given a natural-language goal and a stream of
screenshots, an agent issues GUI actions; OSWorld's execution-based evaluator
returns a binary score. Metric: aggregate success rate.

**Level 2 — our derived task.** Given a failed agent trajectory, the task
specification, and the human reference, select **every applicable** failure mode
from the taxonomy — ratified 2026-08-10, superseding the frozen taxonomy's
one-primary policy. Metric: per-leaf inter-annotator agreement (human–human as
upper bound, human–judge as the calibration target), each leaf treated as an
independent binary presence decision.

> ⚠️ The judge prompt and the agreement code still assume one primary label. See
> the migration checklist in [`03-failure-taxonomy.md`](03-failure-taxonomy.md) —
> it must be finished before discovery labeling, or agreement numbers will be
> wrong without being obviously wrong.

## The judge input bundle

Required context for attribution as of `osworld_v1` and later:

- **Canonical task instruction** from the OSWorld task JSON — *not* only the
  agent-visible or trajectory-truncated string
- **OSWorld evaluator bundle**: outcome (`result.txt`), the `evaluator` rules, and
  a **per-func summary** of what the metric checks. Do not dump all OSWorld
  metrics. Implementations: `xlang-ai/OSWorld/tree/main/desktop_env/evaluators/metrics`
- **Model observation** at `t*` with predicted click/action overlay when available
- **Executed action** vs **model code (CoT)** vs **stated intent** at `t*`
- Previous 2–3 steps, compressed
- Evaluator failure message / failed assertion when available, else binary score
  plus the eval bundle
- Taxonomy decision tree for confusable pairs
- **Human reference path (non-binding)**: the full OSWorld-Human / Human Agent
  sequence — each step's action text plus observation screenshot where artifacts exist

Canonical worked example — task `06fe7178-4491-4589-810f-2e2bc9502122` (Chrome),
evaluator `is_expected_tabs`:

```json
{ "evaluator": { "func": "is_expected_tabs",
    "result":   { "type": "open_tabs_info" },
    "expected": { "type": "rule",
      "rules": { "type": "url", "urls": [
        "https://www.lonelyplanet.com",
        "https://www.airbnb.com",
        "https://www.tripadvisor.com" ] } } } }
```

### Trace step semantics — four distinct things

A subtlety that is easy to get wrong when reading `traj.jsonl`-style logs:

| Field | Meaning |
|---|---|
| **Observation (before action)** | Screenshot at step *k* — the UI state when choosing action *k* |
| **Executed action (trajectory)** | What the runtime actually ran on the VM, often absolute pixels |
| **Model code (CoT)** | The code block in the model response, often normalized 0–1 coords |
| **Stated intent (CoT)** | The natural-language `## Action:` section |

Post-action visual state is the **next** step's observation — typical HF zips have
no separate post-image. A programmatic `grounding_mismatch` flag marks executed-vs-
proposed coordinate divergence beyond tolerance after normalization. That is
**evidence** for Click Region Error / Location Hallucination / Fine-Grained
Manipulation — it is **not** a taxonomy leaf.

## The Human Agent (oracle)

An executor inside the OSWorld Docker/VM that replays OSWorld-Human
`human-ground-truth` actions and captures an **observation screenshot before each
action**. Outputs feed the annotators' human column and the multimodal judge.

It is explicitly **not** an OpenCUA model run, not training data, and not a gold
path the agent must match.

| Tier | Examples | Executor |
|---|---|---|
| Deterministic | `HOTKEY`, `TYPING`, `PRESS` | direct desktop control |
| Semi | `CLICK` cell G1, sheet names | parse + UI automation |
| Grounded | `CLICK` pivot table icon | frontier VLM → coords → execute |

Artifacts land at `config/osworld/<pin>/oracle/<domain>/<task_id>/` with
`human_traj.json`, `human_step_N_obs.png`, and `grounding_cache.jsonl`.
`oracle_status` ∈ `ready` (all steps executed) / `partial` (some grounded steps
failed, ship what exists) / `failed` (text-only human ref in the UI) / `pending`.

**Rejudge gate:** the multimodal `osworld_v1` rejudge only runs once
`oracle_status` is `ready` or `partial`.

## Review tooling

Multi-annotator workflow for **taxonomy discovery** on paired pilot traces.

| Field | Value |
|---|---|
| Packet ID | `pilot_taxonomy_paired_20260703` |
| A3B run | `20260626_172919_a3b_pilot_full_v4` |
| 7B run | `20260626_172922_7b_pilot_full_v4` |
| Scope | 30 pilot tasks, paired A3B + 7B per task (60 traces) |
| Purpose | Qualitative taxonomy discovery **before** revising `failureTaxonomy.md` |
| Annotators | `abdoul`, `raghav` — always pass `--annotator` |

Judge labels are frozen in `packet_manifest.json`; human labels live in a shared
`annotations.json` on Babel, namespaced per annotator. Day-to-day work is **laptop
labeling** — pull packet once, then per session pull annotations → serve locally →
label in browser → auto-push. **Labeling never runs on Babel compute nodes.**
Detail: `errorAnalysis/docs/trace_review_labeling.md`.

## Built vs. planned

| Component | Status |
|---|---|
| OpenCUA A3B + 7B pilot trajectories (v4 runs) | **Working** |
| OpenCUA A3B adapter, Tier-1 attribution on Babel HF pipeline | **Working** — zero adapter gaps |
| Anthropic Claude judge in the HF pipeline (`claude-sonnet-4-6` default) | **Working** |
| Paired-pilot HTML trace review, in-page taxonomy labeling | **Working** |
| Multi-annotator annotations + Babel sync scripts | **Working** |
| Shared mattlab Babel project root + shared venv | **Working** |
| OSWorld context vendoring, enriched judge wiring, approved mockups | **Working** (`4829e57`) |
| vLLM serving on Bridges-2 (0.11.0) | **Working** |
| Grounding reproduction (ScreenSpot V2, OSWorld-G @ 7B/32B) | **Done** |
| Human Agent (oracle) screenshots per step | **In progress** — gates the rejudge |
| Provisional multimodal rejudge `osworld_v1` | **Blocked** on `oracle_status` |
| Discovery labeling by abdoul + raghav | **Not started** — next after infrastructure |
| Inter-annotator agreement numbers | **Not started** |
| Calibrated judge | **Not achieved** — explicitly out of scope this milestone |
| Prevalence with CIs | **Not started** — Phase D |
| Controlled tracks (zoom / ambiguity / infeasible / relational / cross-app) | **Not started** |

## Success criteria (unchanged, still the right bar)

- Per-model prevalence for every leaf at `t*`, with confidence intervals
- Co-occurrence matrix among leaves; propagation rates
- **Per-leaf** inter-rater κ (not overall κ only), target ≥ 0.6 where feasible
- Judge-vs-human agreement per leaf, 5+ anchors each
- Hidden Operation Blindness rate reported for OSWorld
- Cross-Application Context Loss reported on `cross_app`-tagged tasks only

Explicitly **not sufficient**: success rates alone, or an uncalibrated judge pie chart.

## Stretch goal — Visual Trajectory Steering (VTS)

Conditional, and currently well behind the infrastructure work. Detailed in
[`06-idea-bank.md`](06-idea-bank.md): decompose GUI tutorial videos into visually
marked keyframes, convert each to a short text heuristic, and inject them as
**latent KV banks** via Memory Inception rather than visible prompt text —
targeting action looping and long-horizon memory failure without consuming a small
model's context window.
