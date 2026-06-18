# Failure Analysis Experiment Plan

This document defines **what we run** (models, environment, controlled tracks, metrics). For **how we label and validate failures**, see [failureStudyProtocol.md](failureStudyProtocol.md). For category definitions, see [failureTaxonomy.md](failureTaxonomy.md).

**Primary deliverable:** A publishable, human-validated failure taxonomy with quantitative prevalence on a stratified OSWorld subset (not a full leaderboard sweep).

**Master plan:** [failureAnalysisFinalPlan.md](failureAnalysisFinalPlan.md)

---

## I. Failure taxonomy reference

All observed failures are classified using the **16-leaf taxonomy** in [failureTaxonomy.md](failureTaxonomy.md):

**Perception and Grounding (6 leaves):** Click Region Error, Visual Confusion (Primitive Reliance), Text Matching Bias, Resolution/Scale Brittleness, Fine-Grained Manipulation Failure, Software Commonsense (Icon Recognition) Failure

**Cognitive and Planning (10 leaves):** Action Looping, Location Hallucination, Spatial Reasoning Error, Goal Hallucination, Reasoning Drift, Long-Horizon Memory Failure, Instruction Ambiguity Failure, Refusal/Infeasibility Error, Hidden Operation Blindness, Cross-Application Context Loss

**Meta-labels (orthogonal):** `evaluator_mismatch`, `propagated_failure` — see [failureStudyProtocol.md](failureStudyProtocol.md).

---

## II. Additional phenomena (not taxonomy leaves)

Track separately from the 16 leaves:

| Phenomenon | Treatment |
|---|---|
| **Context Saturation Latency** | Systems metric: plot action latency / accuracy vs context length — appendix, not a failure leaf |
| **Evaluator Bypass (false positives)** | Meta-label `evaluator_mismatch` + human audit protocol |
| **Code-Solution Bias** | Separate tool-enabled branch only; do not mix with GUI-only failure prevalence |

---

## III. Experimental setup

### Models for comparison

| Role | Model | Inference |
|---|---|---|
| Ultra-small agent | Qwen3.5-VL-0.8B | vLLM on Bridges-2 (`GPU-shared`) |
| Trained small CUA baseline | OpenCUA-7B | vLLM on Bridges-2 (`--trust-remote-code`) |
| Optional mid / frontier | OpenCUA-32B, GPT-4o, or Claude | vLLM or API |

Lock across all models: action space, max steps, observation type (screenshot), temperature, CoT format, and inference engine settings. Document all configs in run manifests.

### Environment

- **Base:** OSWorld-Verified (containerized), default conditions for the **standard track**
- **Compute:** **PSC Bridges-2** (primary; active allocation) for vLLM inference and offline eval. **CMU Babel** (secondary; account pending). OSWorld VMs per group policy — see [failureStudyProtocol.md](failureStudyProtocol.md#compute-infrastructure)

### Controlled tracks (separate result tables)

| Track | Modification | Taxonomy leaves |
|---|---|---|
| **Standard** | OSWorld-Verified defaults | All leaves |
| **Variable visuals** | Randomized wallpapers, icon themes, browser zoom 70%–150% | Resolution/Scale Brittleness |
| **Ambiguity injection** | ~20% underspecified instructions | Instruction Ambiguity Failure |
| **Infeasible tasks** | Tasks impossible in current UI state | Refusal/Infeasibility Error |
| **Cross-app** | Multi-application OSWorld tasks | Cross-Application Context Loss |
| **Relational grounding** | "Click X" vs "Click the button left of Y" variants | Spatial Reasoning Error, Text Matching Bias |

Do **not** combine stress-track results with standard-track prevalence tables.

### Action space

- **Primary:** GUI-only (screenshot + pyautogui-style actions) for failure attribution
- **Secondary branch:** Tool-enabled runs for Code-Solution Bias analysis only

### Interventions (future ablation — not during initial failure collection)

RegionFocus and Image-as-Map are **post-hoc interventions** to test after baseline failure distributions are measured. Including them in initial runs confounds attribution.

---

## IV. Execution methodology

### Compute scope (agreed)

| Stage | Scope |
|---|---|
| **Pilot** | 30 tasks × 1 seed — pipeline debug on **Bridges-2** |
| **Core study** | **100 stratified tasks × 3 seeds × 2–3 models** |
| Extension (optional) | 200 tasks × 3 seeds |
| Full OSWorld-Verified (optional) | 369 tasks × 3 seeds — not required for taxonomy paper |

Track SU usage with `my_quotas` on Bridges before scaling.

**Reliability:** Use **Pass@3** for the core study. Pass@10 is reserved only if stochasticity becomes a stated research question.

### Stratification (100-task core set)

Balance across:

- Application domain (browser, office, media, dev tools, OS settings)
- Task step length (short / medium / long horizon)
- Failure-mode tags: include tasks tagged `relational`, `cross_app`, `fine_manipulation`, `underspecified`, `infeasible` per [failureStudyProtocol.md](failureStudyProtocol.md)

Pre-register the task list before large runs.

### Evaluator audit

Before running, manually review OSWorld eval scripts for **hidden constraints** not stated in the prompt (exact line counts, temp paths, etc.). Log issues as `evaluator_mismatch` candidates.

### Human-in-the-loop simulation

When an agent issues `CALL_USER`, a simulated user provides missing info. Measure success lift separately on the **infeasible/underspecified** tracks — not blended into standard-track rates.

---

## V. Analysis and metrics

Map each metric to specific taxonomy leaves or meta-labels:

| Metric | Maps to |
|---|---|
| **Failure prevalence by leaf** | All 16 leaves at first failure step `t*` — primary outcome |
| **Success-rate decay curve** | Long-Horizon Memory Failure; distinguish propagated vs root-cause |
| **Repetition ratio** | Action Looping (Tier-1 detector) |
| **Relational vs direct grounding score** | Spatial Reasoning Error, Text Matching Bias |
| **Instruction-evaluator mismatch rate** | Meta-label `evaluator_mismatch` |
| **Hidden-operation rate** | Hidden Operation Blindness |
| **Cross-app state retention** | Cross-Application Context Loss (on `cross_app` tasks only) |
| **Zoom regression delta** | Resolution/Scale Brittleness (zoom stress track only) |
| **Inter-rater κ / judge agreement** | Validation — per leaf, not overall |

### Attribution pipeline

Failed runs are processed per [failureStudyProtocol.md](failureStudyProtocol.md):

1. Identify first failure step `t*`
2. Apply Tier-1 programmatic detectors
3. VLM judge on unresolved cases (screenshot + CoT at `t*`)
4. Human gold set (150–200 steps) for calibration

---

## VI. Infrastructure

### OpenCUA + vLLM (required for OpenCUA agent)

```bash
vllm serve xlangai/OpenCUA-7B \
  --trust-remote-code \
  --served-model-name opencua-7b \
  --host 0.0.0.0 \
  --port 8000
```

OSWorld: `run_multienv_opencua.py` with `--coordinate_type qwen25`, pointing at `http://<babel-gpu-node>:8000/v1`.

Requires **vllm >= 0.12.0**.

### Qwen3.5-VL agent

Separate vLLM config and OSWorld adapter ([OSWorld #441](https://github.com/xlang-ai/OSWorld/issues/441)). Do not reuse OpenCUA chat template.

### OpenTau

**Not used** for this study. [OpenTau](https://github.com/TensorAuto/OpenTau) is a robotics VLA training toolchain. Use [OpenCUA](https://github.com/xlang-ai/OpenCUA) + AgentNetBench instead.

### AgentNetBench pilot

Run offline on **Bridges-2** before large OSWorld VM spend to validate Click Region, Text Matching, and Location Hallucination detectors.

---

## VII. Success criteria

The experiment phase is complete when we can report, with confidence intervals:

1. Per-model prevalence for all **16 leaves** at `t*`
2. Co-occurrence and propagation rates
3. Human inter-rater κ and judge-vs-human agreement **per leaf**
4. OSWorld-specific rates for **Hidden Operation Blindness** and **Cross-Application Context Loss**

We are **not** done with success rates alone or an uncalibrated judge pie chart.
