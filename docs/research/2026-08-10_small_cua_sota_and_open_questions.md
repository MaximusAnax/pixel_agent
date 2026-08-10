# Small-model CUA landscape — grounding SOTA, OSWorld status, context design, oracle-replay prior art

> Answers PROJECT_STATE open questions: small-model SOTA on grounding and
> OSWorld; frame-sequence vs single-frame training; screenshot-history
> effects; OSWorld relevance in 2026; Oracle-Agent prior art. Compiled
> 2026-08-10 by a Claude research agent (GitHub READMEs fetched directly;
> arXiv/HF/leaderboard sites blocked by sandbox proxy — those numbers are
> search-snapshot-sourced; aggregator-only numbers flagged
> `[unverified-aggregator]`).

## 1. GUI grounding SOTA for small models (mid-2026)

Benchmarks: ScreenSpot (saturated), ScreenSpot-V2 (~92–95 for good 7–8Bs),
**ScreenSpot-Pro** (still discriminative), **OSWorld-G** (variant-sensitive).

### ≤8B class (ranked by ScreenSpot-Pro)

| Model (size, base) | Date | SS-Pro | OSWorld-G | SS-V2 | Source |
|---|---|---|---|---|---|
| **UI-Venus-1.5-8B** | Feb 2026 | **68.4** (73.9 w/ ZoomIn) | 69.7 | n/r | [repo](https://github.com/inclusionAI/UI-Venus), arXiv:2602.09082 |
| **MAI-UI-8B** (Tongyi) | Dec 2025 | 65.7 | 60.1 | n/r | [repo](https://github.com/Tongyi-MAI/MAI-UI), arXiv:2512.22047 |
| **Step-GUI-8B** | Dec 2025 | 62.6 | **70.0** | **95.1** | arXiv:2512.15431 |
| GUI-Owl-1.5-8B | Feb 2026 | (family flagship 72.9/80.3 w/ crop) | — | — | [repo](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5), arXiv:2602.16855 |
| Qwen3-VL-8B-Instruct | Oct 2025 | 52.7–54.6 | 57.5–58.2 | 92.1 | arXiv:2511.21631 |
| Holo1.5-7B | Sep 2025 | 57.9 | n/r | ~93 | [H blog](https://hcompany.ai/holo1-5-open-foundation-models-for-computer-use-agents) |
| GUI-Owl-7B | Aug 2025 | 54.9 | n/r | ~93 | arXiv:2508.15144 |
| GTA1-7B | Jul 2025 | 50.1 | 67.7 | 92.4 | arXiv:2507.05791 |
| OpenCUA-7B | Aug 2025 | 50.0 | 55.3 | 92.3 | [repo](https://github.com/xlang-ai/OpenCUA) |
| UI-TARS-1.5-7B | Apr 2025 | 49.6 (repro disputed) | n/r | ~94 | [repo](https://github.com/bytedance/UI-TARS) |
| Jedi-7B | May 2025 | ~36–39.5 | ~54–55 | ~91 | arXiv:2505.13227 |
| Qwen2.5-VL-7B (baseline) | Feb 2025 | ~27–29 | ~31 | ~88 | arXiv:2502.13923 |

### ≤3B class

| Model | Date | SS-Pro | OSWorld-G |
|---|---|---|---|
| **UI-Venus-1.5-2B** | Feb 2026 | **57.7** (64.6 w/ ZoomIn) | 59.4 |
| MAI-UI-2B | Dec 2025 | 57.4 | n/r |
| Step-GUI-4B | Dec 2025 | n/r | 66.9 |
| SE-GUI-3B | 2025 | 35.9 | n/r |
| Jedi-3B | May 2025 | ~32–36 | ~47–51 |
| UGround-V1-2B | Jan 2025 | 26.6 | n/r |

**Trends:** today's 2B class (~58 SS-Pro) matches mid-2025's best 72Bs.
Test-time zoom/crop adds ~5–7 points and is now standard in SOTA claims —
compare like-for-like. Icon-vs-text asymmetry noted in the meeting matches
this data: text grounding saturated, professional/icon-dense (SS-Pro) is the
discriminator.

## 2. OSWorld end-to-end; v1 vs v2

### Small open models (≤9B), OSWorld-Verified

| Model | Date | Score | Notes |
|---|---|---|---|
| **GUI-Owl-1.5-8B-Thinking** | Feb 2026 | **52.9** | Qwen3-VL base |
| Step-GUI-8B | Dec 2025 | 48.5 | arXiv:2512.15431 |
| GUI-Owl-1.5-4B | Feb 2026 | 48.2 | |
| AutoGLM-OS-9B | Aug 2025 | 48.1 | ⚠ API-GUI hybrid, not pure vision (arXiv:2508.14040) |
| **GUI-Owl-1.5-2B** | Feb 2026 | 43.5 | ≤3B record |
| GUI-Owl-7B | Aug 2025 | 34.9 | |
| UI-TARS-1.5-7B | Apr 2025 | 27.5 | |
| OpenCUA-7B | Aug 2025 | 26.6 @100 steps | |

(GTA1-7B's 45.2 uses an o3-class planner — compound system, not ≤8B e2e.)

### Frontier progression (v1-Verified)

Claude Sonnet 4.5 61.4 (Sep 2025) → Opus 4.5 66.3 → Holo3-122B-A10B 78.9 →
Qwen-UI-Agent 79.5 (arXiv:2607.28227) → Opus 4.8 ~83.4 → Aug 2026 top:
Qwen3.8-Max 86.1 / Claude Fable 5 85.0 `[unverified-aggregator]`; at/above
the 72.4% human baseline ([Epoch](https://epoch.ai/benchmarks/os-world)).

### OSWorld 2.0 (Jun 2026)

arXiv:2606.29537, [repo](https://github.com/xlang-ai/OSWorld-V2). 108
long-horizon workflows (~1.6h human median, ~318 tool calls/task), 31
self-hosted sites (drift-proofing), checkpoint partial credit (avg
27.25/task). Best: Claude Opus 4.8 **20.6%**; GPT-5.5 ~13%.

## 3. Frame sequences vs single frames (training + inference context)

**All major native CUA models train on multi-step trajectories; they differ
in how much visual history enters context:**

- **UI-TARS** (arXiv:2501.12326): natively multi-turn; previous N
  screenshots+actions; state-transition captioning; deployed SDK caps history
  images at **5**. UI-TARS-2 adds multi-turn online RL.
- **OpenCUA** (arXiv:2508.09123): **up to 3 screenshots** (current + 2
  history) + concise L1 text action history; ablation shows 3 images + L1
  text is the sweet spot; denser L2 text history is *worse* at inference.
- **Qwen2.5-VL** (arXiv:2502.13923): video-trained (dynamic-FPS, absolute-time
  mRoPE), but its own agent recipe is **single current screenshot + text
  action history**.
- **Qwen3-VL** (arXiv:2511.21631): explicitly sequence-oriented
  (Interleaved-MRoPE, 256K interleaved, more video/agent pretraining data) —
  the base of everything SOTA-small in 2026.

**Is screenshot history harmful?** Evidence says "helps a little, costs a
lot, redundant/ambiguous if naive" — no published result that
action-history-only strictly beats screenshot history at matched budgets:

- SimpAgent (ICCV 2025, arXiv:2507.03730): high redundancy; consistency-guided
  history compression + masking beats naive full context at −27% FLOPs.
- HiconAgent (CVPR 2026, arXiv:2512.01763): repetitive history screenshots
  cause visual ambiguity; but fully dropping them loses 1.7–3.1%.
- Aria-UI (arXiv:2412.16256): interleaved image-text history *improves*
  dynamic grounding.
- **Open niche:** a screenshot-history vs action-history-only ablation on
  *failure categories* (not just success rate) is unpublished — directly
  answerable with our judge pipeline (`include_screenshot` /
  `prev_steps_k` knobs in autoResearch).

## 4. Is OSWorld still relevant in 2026?

**Relevant but transitional.** Frontier saturated Verified (~83–86%);
small/open models (26–53%) have big headroom, so it remains the right
yardstick for small-model error analysis. Known v1 issues: ~10% task validity
errors pre-Verified ([Epoch analysis](https://epoch.ai/blog/what-does-osworld-tell-us-about-ais-ability-to-use-computers)),
web drift (fixed via Verified + v2 self-hosting), binary scoring (v2:
checkpoints), memorization risk (v2: gated assets). Successors/extensions:
OSWorld 2.0, OSWorld-MCP, OSWorld-Human, WindowsAgentArena-V2, OS-Marathon.
**Recommendation: OSWorld-Verified pinned release + v2-style checkpoint
partial credit for analysis granularity.**

## 5. Oracle-Agent prior art (human-demo replay)

- **OSWorld-Human** (arXiv:2506.16042): human reference trajectories for all
  369 tasks; used for *efficiency scoring* (WES±), not screenshot replay.
- **PC Agent-E / Trajectory Boost** (arXiv:2505.13909): closest prior art —
  replays human steps as state snapshots, branches alternative actions with a
  strong model, trains PC Agent-E (+141% rel. over Qwen2.5-VL-72B on
  WindowsAgentArena-V2) from only 312 trajectories.
- **Teacher-forced offline benchmarks** (Mind2Web, AndroidControl,
  AgentNetBench): the implicit oracle-replay paradigm; offline step accuracy
  correlates imperfectly with online success.
- **WebCanvas key nodes** (arXiv:2406.12373) → ancestor of v2 checkpoints.
- **Demos as guidance:** Synapse, Agent Workflow Memory, Learn-by-Interact
  (ICLR 2025: +11.1pp OSWorld for Claude-3.5 via synthesized demo retrieval).
- Raw material: [xlangai/ubuntu_osworld_verified_trajs](https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs)
  (430GB agent trajectories with screenshots).
- **Verdict: no published system replays OSWorld human demos action-by-action
  to regenerate per-step screenshots for grounding-vs-planning failure
  attribution.** The team's Oracle Agent idea is a defensible contribution;
  nearest neighbors are components, not integrations.

## Implications for pixelAgent

1. **Grounding is no longer the small-model bottleneck** (≤8B: 62–74 SS-Pro,
   ~70 OSWorld-G) while e2e success lags (43–53%) — the interesting failures
   moved up the stack (planning, state tracking, recovery, termination),
   which is what per-step oracle-replay analysis isolates.
2. **Baseline choice:** GUI-Owl-1.5 (2B/4B/8B) is the strongest small e2e
   family; UI-Venus-1.5/Step-GUI for grounding ablations; OpenCUA-7B remains
   best-documented for controlled studies. (No OpenCUA-3B exists.)
3. **Context design:** current screenshot + ≤3 visual history + full text
   action history is the convention; the failure-category-level screenshot
   ablation is an open, cheap, novel experiment.
4. **Benchmark strategy:** OSWorld-Verified pinned + checkpoint-style partial
   credit; interpret per-task.
5. **Oracle-replay niche is open** — combine OSWorld-Human trajectories with
   a replay harness for divergence-point detection; PC Agent-E suggests the
   same replayed states also yield cheap corrective training data.
