# 5 — Literature

Organized by the role each paper plays in the argument, not alphabetically. The
canonical link list is the Drive **Reading List**; this file records *why each
one matters to us*.

---

## Tier 1 — load-bearing

The pipeline does not make sense without these.

| Paper | Link | Why it matters |
|---|---|---|
| **OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments** (Xie et al., 2024) | [arXiv 2404.07972](https://arxiv.org/pdf/2404.07972) | The benchmark the entire pipeline is built around. 369 tasks, 9 real desktop/web apps, per-task execution-based evaluator returning a binary score. Establishes the human-vs-agent capability gap we study. |
| **OSWorld-Human: Benchmarking the Efficiency of Computer-Use Agents** (Abhyankar et al., 2025) | [arXiv 2506.16042](https://arxiv.org/html/2506.16042v1) · [project post](https://mlsys.wuklab.io/posts/oshuman/) · [data](https://github.com/WukLab/osworld-human) | Human-validated correct steps for all 369 tasks, in `single-action` and `grouped-action` form. Built for *efficiency* analysis; **we repurpose the trajectories as the reference signal for failure diagnosis** — a different use of the same dataset, and the core of our novelty claim. |
| **SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents** (Cheng et al., 2024) | [arXiv 2401.10935](https://arxiv.org/pdf/2401.10935) | Introduces GUI grounding pretraining and the ScreenSpot benchmark. Its finding that grounding accuracy is the main bottleneck for downstream GUI task success is *the* reason perception/grounding is a separate taxonomy branch from planning. |
| **Scaling Computer-Use Grounding via UI Decomposition and Synthesis / OSWorld-G** (Xie et al., 2025) | [arXiv 2505.13227](https://arxiv.org/pdf/2505.13227) | Fine-grained manipulation and layout-understanding grounding benchmark. Used with ScreenSpot V2 to validate our vLLM serving stack before trusting any OSWorld rollout. |
| **OSWorld-Verified** | [xlang.ai blog](https://xlang.ai/blog/osworld-verified) | The variant frontier labs actually report on. Named repeatedly as the target in planning docs — but **never cited in the SURA report**. Fix that. |
| **OpenCUA** | [github.com/xlang-ai/OpenCUA](https://github.com/xlang-ai/OpenCUA) | The agent codebase. 3B and 7B are our rollout models; the oracle agent that replays human actions is being built inside it. |

## Tier 2 — shaped the taxonomy

| Paper | Link | Why it matters |
|---|---|---|
| **Qwen3-VL Technical Report** (Bai et al., 2025) | [arXiv 2511.21631](https://arxiv.org/pdf/2511.21631) | Source of the icon-vs-text grounding gap. Small open-weight VLMs (0.6B–9B) trail far behind on **icon-based** grounding while text grounding is near-saturated → why icon/software-commonsense recognition is its own leaf. |
| **Qwen2-VL** (Wang et al., 2024) | [arXiv 2409.12191](https://arxiv.org/pdf/2409.12191) | Base architecture our agent models build on. |
| **ScreenSpot-Pro: GUI Grounding for Professional High-Resolution Computer Use** (Li et al., 2025) | [arXiv 2504.07981](https://arxiv.org/pdf/2504.07981) | Best model of any size solves under 19% of instructions → grounding failure is not solely a small-model problem. |
| **GUI-Perturbed: Domain Randomization Reveals Systematic Brittleness in GUI Grounding Models** (Wang et al., 2026) | [arXiv 2604.14262](https://arxiv.org/pdf/2604.14262) | Independently varying scene and phrasing costs 27–56 points for models above 85%. Evidence that static grounding accuracy overstates robustness → benchmark/environment artifacts deserve their own category. |
| **On the Reliability of Computer Use Agents** (Gonzalez-Pumariega et al., 2026) | [arXiv 2604.17849](https://arxiv.org/pdf/2604.17849) | Repeated executions of the same OSWorld task show much apparent unreliability traces to execution stochasticity and task-specification ambiguity. **Independent confirmation of exactly the benchmark noise we hit.** Strongest external support for the pivot. |
| **Uground** | — | Spatial reasoning for grounding; motivates the Spatial Reasoning Error leaf. |
| **Computer Agent Arena** | [OpenReview](https://openreview.net/pdf?id=3x4SDbXbgl) | Human-centric evaluation and analysis of CUAs. |

## Tier 3 — judge calibration (the closest prior art)

**These are the papers a reviewer will compare us against.** They came out of our
own literature report (2026-07-03) and are currently missing from the SURA
report's related work — the single biggest citation gap.

| Paper | Link | What we take from it |
|---|---|---|
| **AgentRewardBench: Evaluating Automatic Evaluations of Web Agent Trajectories** | [arXiv 2504.08942](https://arxiv.org/html/2504.08942v2) | The closest benchmark for calibrating a trajectory judge against human labels. Finding: judges miss nuanced issues and **over-trust agent reasoning** → we should ablate the judge with CoT withheld. |
| **An Illusion of Progress? / WebJudge / Online-Mind2Web** | [arXiv 2504.01382](https://arxiv.org/html/2504.01382v4) | ~85% human agreement via key-point + key-screenshot selection. Template for reducing long-trace token load before judgment. Judges degrade on both too little and too much unfiltered evidence. |
| **TRAIL: Trace Reasoning and Agentic Issue Localization** | [arXiv 2505.08638](https://arxiv.org/abs/2505.08638) | Fine-grained reasoning/planning/execution taxonomy over long structured traces; best model only 11% joint accuracy. Calibrates how hard our task is. |
| **AgentRx: Diagnosing AI Agent Failures from Execution Trajectories** | [arXiv 2602.02475](https://arxiv.org/abs/2602.02475) | Generate constraints → validate step by step → pass **evidence packet** to the judge. Blueprint for "structured evidence first, LLM second." |
| **AgentProcessBench: Diagnosing Step-Level Process Quality in Tool-Using Agents** | [arXiv 2603.14465](https://arxiv.org/html/2603.14465v2) | Ternary step labels (+1 / 0 / −1) with an error-propagation rule. Models struggle most on neutral-vs-incorrect — mirrors our `propagated_failure` problem. |
| **Learning from Failure: Inference-Time Self-Improvement for Computer-Use Agents** (Sun et al., 2026) | — | Closest in *goal*: diagnose CUA failure modes and turn them into inference-time fixes. **We differ** by conditioning the diagnosis on a human reference trajectory and by explicitly calibrating against human annotators before trusting output. |
| **WebSuite** | [arXiv 2406.01623](https://arxiv.org/pdf/2406.01623) | Diagnostic web action taxonomy linking task failures to interaction classes. |
| **From Grounding to Planning: Benchmarking Bottlenecks in Web Agents** | [arXiv 2409.01927](https://arxiv.org/html/2409.01927v1) | Argues **planning**, not grounding, is the main bottleneck on the web — a useful counterweight to our grounding-first prior. Suggests OSWorld-Human comparisons should emphasize planning divergence over raw click mismatch. |

### The novelty finding

Our literature report's bottom line, as of 2026-07-03:

> No paper was found that uses OSWorld-Human's human trajectories to calibrate a
> failure-analysis judge, or to compare model failure traces against human-correct
> traces. Later papers (Step-level Optimization for Efficient Computer-use Agents,
> OSExpert, AgentAtlas) cite OSWorld-Human as **efficiency motivation only** —
> citation-level uptake, not trace-level reuse.

So the gap is real: human-trajectory datasets give you what a correct path looks
like; judge benchmarks give you how humans label bad trajectories; **nothing joins
them in computer use.** That is the publishable combination.

### Judge design implications from this literature

The report recommends a layered judge rather than a "read the whole trace and
decide" LLM:

1. **Reference-trace alignment** — align the model trace to OSWorld-Human's
   grouped and single traces.
2. **Evidence selection** — pick key milestones and keyframes (WebJudge), don't
   dump the full trace into context.
3. **Step-level rubric** — label each aligned step *progressing / neutral-redundant
   / recoverable deviation / goal-breaking deviation*, then locate the **first
   irrecoverable divergence**.
4. **Failure taxonomy** — a small explicit label set, not open-ended prose.

And two design cautions that matter a lot:

- **Reference-guided, not reference-bound.** A model may deviate from the human
  path and still be correct. Multiple valid trajectories exist (WebLINX,
  Mind2Web-derived analyses). Judge on **milestone coverage, avoidable redundancy,
  recoverability, and goal preservation** — never strict sequence matching.
  ✅ **The team formally adopted this on 2026-07-10** ("Human reference is
  non-binding"), and it is now written into both `failureStudyProtocol.md` and the
  frozen `failureTaxonomy.md`. The SURA report still reads as reference-*bound* and
  should be softened to match.
- **Evaluate on four targets, not one scalar**: outcome agreement, first-error
  localization, failure-category accuracy, and redundancy calibration (does the
  judge distinguish "correct but overlong" from "incorrect and doomed"?).

## Tier 4 — human-trajectory datasets (context)

| Dataset | Domain | Scale | Relevance |
|---|---|---|---|
| Mind2Web | Web navigation | 2,350 tasks / 137 sites | Precedent for extracting step structure from demonstrations |
| WebLINX | Conversational web nav | 100K interactions, 2,300 demos | Multiple human-valid trajectories per intent |
| Android in the Wild | Mobile | 715K episodes | Large-scale human UI behavior |
| MolmoWeb human subset | Web | 36K trajectories, 623K steps | Segments human traces into reusable subtask/skill units |
| PC Agent-E | Windows computer use | 312 trajectories | Small curated OS traces + synthetic augmentation |
| CUA-Suite | Computer use video | — | [arXiv 2603.24440](https://arxiv.org/abs/2603.24440) Massive human-annotated video demonstrations |

Pattern: these are used for **training, adaptation, or replay** — not for judging
failure against a gold trace. That is the gap.

> Counter-signal worth remembering: MolmoWeb found that at equal sample count,
> **synthetic** trajectories outperformed human-only training data. High-quality
> human traces are most valuable as **anchors and calibration targets**, not
> necessarily as the primary training signal.

## Tier 5 — stretch goal and adjacent

| Paper | Link | Role |
|---|---|---|
| **Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs** (Liu et al., 2026) | [arXiv 2605.06225](https://arxiv.org/pdf/2605.06225) | Foundation of the VTS stretch goal. Training-free latent steering; 6.4–118× KV-cache reduction; position-agnostic (pre-RoPE canonical keys); robust past 24+ turns. |
| **Let's Verify Step by Step** (Lightman et al., 2023) | [arXiv 2305.20050](https://arxiv.org/pdf/2305.20050) | Process supervision beats outcome supervision — conceptually what we want from the judge: a signal that localizes *which step broke*, not just that the task failed. |
| **Visual Test-time Scaling for GUI Agent Grounding** (RegionFocus) | [arXiv 2505.00684](https://arxiv.org/pdf/2505.00684) | 7B + RegionFocus reportedly surpasses 72B on grounding. Candidate modular plug-in. |
| **Molmo2: Open Weights and Data for VLMs with Video Understanding and Grounding** | [arXiv 2601.10611](https://arxiv.org/pdf/2601.10611) | The "fully open source" alternative to Qwen — enables studying how backbone properties affect downstream CUA performance. |
| **Stable Diffusion 3** | [arXiv 2403.03206](https://arxiv.org/pdf/2403.03206) | Backing for the diffusion-based grounding-label idea. |
| **Learning from Online Videos at Inference Time for Computer Use Agents** | — | Video-as-guidance at inference; adjacent to VTS. |
| **Video Understanding with LLMs: A Survey** | — | Background for whether current CUA models understand frame *sequences* at all. |
| **TheAgentCompany** | [arXiv 2412.14161](https://arxiv.org/pdf/2412.14161) | Alternative benchmark under consideration. |
| **How Do AI Agents Do Human Work?** | [arXiv 2510.22780](https://arxiv.org/abs/2510.22780v2) | Alternative benchmark / framing. |
| **AlphaStar / StarCraft II** | [DeepMind](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/) · [Nature](https://www.nature.com/articles/s41586-019-1724-z) | Real-time-strategy detour — explored, did not go anywhere. Kept for the record. |
| **Building an open coding agent (Sera)** — Tim Dettmers | [blog](https://timdettmers.com/2026/01/27/building-open-coding-agent-sera/) | Background on why small models are a defensible moat; security/privacy incentive. |
