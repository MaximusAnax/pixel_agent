# 3 — Failure taxonomy

> **Read this before citing "the taxonomy."** Three versions are in circulation and
> they do not agree. Using the wrong one in a paper, a judge prompt, or an
> annotation rubric will produce labels that cannot be compared across artifacts.
>
> **`errorAnalysis/failureTaxonomy.md` is authoritative and is a FROZEN grounding
> doc** (`GROUNDING_MANIFEST.md`, 2026-07-10, signed off by Abdoul). It may not be
> edited without a new approved plan. Taxonomy leaf additions are deferred unless
> Abdoul requests them, and revisions are meant to come from **human discovery
> labels** — never from provisional judge disagreement alone.

## The three versions

| | **V1 — Drive draft** | **V2 — repo, frozen** | **V3 — SURA report / EOS** |
|---|---|---|---|
| Source | `Taxonomy of CUA Failure Modes` (Drive, 2026-06-12) | `errorAnalysis/failureTaxonomy.md` v1.0 | `PixelAgent_Research.pdf` Table 2; EOS report appendix |
| Top-level categories | 2 | 2 | **3** |
| Perception/grounding leaves | 6 | 6 | 6 |
| Cognitive/planning leaves | 8 | **10** | 8 |
| Benchmark/environment leaves | — | — (handled as meta-label) | **3** |
| Decision rules | no | **yes** | no |
| Meta-labels | no | `evaluator_mismatch`, `propagated_failure` | no |
| Total model-failure leaves | 14 | **16** | 14 |

### What changed, and when

**V1 → V2** added two cognitive/planning leaves and the entire labeling
apparatus:

- **Hidden Operation Blindness** (leaf 15) — goal understood, but the agent only
  tries visible/salient controls when ground truth requires a menu, shortcut,
  context menu, or sidebar tab. *Example: a LibreOffice Impress transition task
  where the agent keeps clicking top-level menus instead of opening the
  right-sidebar tab.*
- **Cross-Application Context Loss** (leaf 16) — task-relevant state lost across
  an app switch (clipboard, file handle, sub-goal progress). *Example: copies
  terminal output but pastes stale clipboard content into a spreadsheet.*

**V2 → V3** promoted benchmark artifacts to a top-level category — and silently
dropped leaves 15 and 16.

## ⚠️ Open discrepancy — needs a decision

The SURA report's Appendix B is presented as "the full taxonomy … as used to
prompt the judge and to guide human annotators." It is not the full taxonomy:
**Hidden Operation Blindness and Cross-Application Context Loss are missing.**

This matters concretely:

- The master plan's success criteria explicitly require *"Hidden Operation
  Blindness rate reported for OSWorld"* and *"Cross-Application Context Loss on
  `cross_app` tasks only."* A judge prompted from the report's table cannot
  produce either number.
- Root `AGENTS.md` forbids modifying `failureTaxonomy.md` without Abdoul's
  approval, so the repo artifact is still authoritatively 16 leaves.
- Hidden Operation Blindness is a *plausible* explanation for a chunk of the
  301 OSWorld failures — dropping it biases labels toward grounding modes.

**Two coherent resolutions.** Either (a) ratify the third category into
`failureTaxonomy.md`, keeping all 16 model leaves → a 3-category / 19-leaf
taxonomy; or (b) keep the frozen 2-category / 16-leaf taxonomy and express
benchmark artifacts through the broadened `evaluator_mismatch` meta-label plus
perhaps one or two more. Option (a) matches how the team talks about the problem
now and makes the third category a *findable result* rather than an annotation
footnote.

**But note the process constraint.** `failureTaxonomy.md` is frozen, leaf additions
are deferred unless Abdoul requests them, and the agreed path is that revisions
follow **human discovery labeling** on the pilot packet. So the right sequence is:
run discovery labeling → see whether benchmark artifacts actually show up as a
distinct thing annotators need → propose the revision in a new approved plan. The
report should not be treated as having settled it.

The 2026-07-10 broadening of `evaluator_mismatch` — now covering "eval criteria
appear met, or the failure is an evaluator artifact, not an agent mistake" — closes
part of the gap. It still does not cleanly cover incomplete human-step instructions
or VM initialization failure, which are properties of the *setup*, not the evaluator.

## The taxonomy (V2 — repo, authoritative today)

### Perception / grounding (6)

| Leaf | Definition | Example |
|---|---|---|
| **Click Region Error** | Identifies the right element conceptually; coordinates fall outside its boundary | Reasons about the "Done" button, clicks just outside it |
| **Visual Confusion (Primitive Reliance)** | Relies on shape/color/position rather than functional semantics | Mistakes a light-colored button for a search box — both white rectangles near the top |
| **Text Matching Bias** | Clicks visible text matching an instruction token instead of the interactive target | Told "click the 'First Name' textbox," clicks the label above the field |
| **Resolution/Scale Brittleness** | Fails to adapt to zoom/resolution change; memorized absolute pixels | At 70% zoom, clicks the empty space where the button sat at 100% |
| **Fine-Grained Manipulation Failure** | Breaks down on character-level cursor placement or compact widgets | Cannot place the cursor between "person" and "1" |
| **Software Commonsense (Icon Recognition) Failure** | Cannot map an unlabeled symbol to its function | Fails to read a magnifying glass as "Search," a gear as "Settings" |

### Cognitive / planning (10)

| Leaf | Definition | Example |
|---|---|---|
| **Action Looping (Repetition)** | Repeats an unsuccessful action without adapting to feedback | Retypes a search term repeatedly, never clicks "Search" |
| **Location Hallucination** | CoT names the right target; coordinates are unrelated to it | Reasons "Notifications is in the left sidebar," outputs coordinates elsewhere |
| **Spatial Reasoning Error** | Misreads relative spatial relations | "Click the link left of 'Side effects'" — right landmark, clicks right side |
| **Goal Hallucination** | Invents intent or sub-goals never specified | Told to click a heart icon, invents "save this to my favorites" |
| **Reasoning Drift** | The CoT itself contains a false claim that misleads the action | Reasons "the logo is at the bottom," clicks an unrelated bottom image |
| **Long-Horizon Memory Failure** | Loses progress or sub-goals after many steps | Converting 20 files, forgets which are done after step ten |
| **Instruction Ambiguity Failure** | Picks a plausible but evaluator-rejected reading of an underspecified task | "Make Times New Roman the default font" — changes only the current document |
| **Refusal/Infeasibility Error** | Fails to recognize an impossible task; clicks speculatively instead of refusing | Told to open Firefox with no Firefox icon present, clicks a random icon |
| **Hidden Operation Blindness** | Goal understood; only visible controls tried; GT needs a hidden affordance | Clicks top-level menus instead of the sidebar tab holding slide transitions |
| **Cross-Application Context Loss** | Loses state across an app boundary | Copies from terminal, pastes stale clipboard into a spreadsheet |

### Benchmark / environment artifact (V3 — proposed third category, 3)

| Leaf | Definition | Example |
|---|---|---|
| **Incomplete human-step instructions** | OSWorld-Human step omits a required action | Says to type into a search bar, never says to press Enter |
| **Premature next-action execution** | Agent acts before the screen finishes updating | Issues the next action mid-render |
| **VM initialization failure** | Required application never finished loading before the trajectory began | Chrome not open on setup |

All three were observed directly in the UI-TARS-72B / OSWorld-Human run. They are
**not model failures** and must not be labeled as such.

## Labeling policy (V2)

- Label at the **first failure step** `t*` — the earliest step where the run is
  irrecoverable or the evaluator fails.
- **Assign every applicable leaf** at `t*`. ✅ **Decided 2026-08-10 (Abdoul):
  all-applicable, not one-primary.**
  - The frozen `failureTaxonomy.md` still reads "exactly one primary root-cause
    leaf per `t*`, secondary leaves optional." That text is now superseded by the
    decision but **not yet edited** — it is a frozen grounding doc. See the
    migration checklist below.
  - De-facto convention already in the review path: human labels are stored as
    `modes_ordered`, an ordered list, and `labels.py` exports
    `modes_ordered[0]` as `<annotator>_primary`. **Decide whether that order is
    meaningful.** If it is a rank, annotators must be told to order deliberately;
    if it is just click order, stop deriving a "primary" from it — otherwise the
    exported primary is an artifact of UI interaction order.
- Apply `propagated_failure` when `t*` is downstream of a root error at `t' < t*`
  — common for Action Looping and Long-Horizon Memory Failure.
- Apply `evaluator_mismatch` when the action is reasonable per the human rubric
  **or the available evidence** but the OSWorld script marks failure — i.e. when
  eval criteria appear met, or the failure is an evaluator artifact rather than an
  agent mistake. *(Broadened at the 2026-07-10 freeze.)*

### Annotator vs. judge boundaries (added 2026-07-10)

These sit inside the frozen taxonomy and govern how labels may be used:

- **Human annotators** (`abdoul`, `raghav`) write gold-in-progress labels to
  `annotations.json`. Their labels are the scientific target for discovery and
  Phase D.
- **The VLM judge** writes versioned provisional labels (`judge_context_version`).
  Treat as reference during discovery — **not** gold. **Do not revise this taxonomy
  from provisional judge disagreement alone.**
- When OpenCUA logs both **CoT model code** and **executed trajectory** actions,
  compare them after coordinate normalization. Divergence supports grounding leaves
  (Click Region Error, Location Hallucination, Fine-Grained Manipulation Failure)
  using screenshot + stated intent. It is **not** a new leaf.
- **Human reference trajectories** are a viable path for cross-reference — **not a
  required path.** Do not label "failure" solely because the agent diverged from the
  human sequence.

### Migration checklist — all-applicable labeling

Decided 2026-08-10. Until every row is done, human and judge labels are **not
comparable** and any agreement number is meaningless.

| # | What | File | Frozen? | Status |
|---|---|---|---|---|
| 1 | Labeling policy: "exactly one primary" → "every applicable leaf" | `failureTaxonomy.md` | **Yes** | ⬜ needs approved edit |
| 2 | Judge prompt says *"Classify the failure at step t\* using EXACTLY ONE primary label"* and *"assign secondary labels only if multiple modes clearly co-occur"* | `src/cua_failure_analysis/judge/prompts.py` (L38, L61) | No | ⬜ |
| 3 | Judge output schema `{primary_mode, secondary_modes[]}` — keep as ordered pair, or flatten to a set? | `judge/prompts.py` L132-135, protocol doc | mixed | ⬜ decide |
| 4 | **`per_leaf_kappa` compares a single label per record** (`r.get(annotator_a) == leaf`, default `label_key="primary_mode"`). Under multi-label it silently measures only the primary — wrong numbers, no error | `src/cua_failure_analysis/labeling/agreement.py` | No | ⬜ **highest risk** |
| 5 | `judge_vs_human_agreement` does exact single-label equality — needs per-leaf binary, or a set metric (Jaccard / exact-set-match) | `labeling/agreement.py` | No | ⬜ |
| 6 | Is `modes_ordered` position meaningful? `labels.py` exports element 0 as `_primary` | `review/labels.py` | No | ⬜ decide |
| 7 | Bump `judge_context_version` when the prompt changes — the existing 16 provisional labels were produced under one-primary | run config | No | ⬜ |

**Good news on the statistic.** Per-leaf Cohen's κ is *better behaved* under
multi-label than under one-primary: each leaf becomes an independent binary
presence decision per trace, which is exactly what `per_leaf_kappa` already claims
to do ("one-vs-rest binary labels"). The function just needs set membership
(`leaf in modes`) instead of equality (`== leaf`). The κ ≥ 0.6 target survives
unchanged.

**What the decision order is now for.** Under one-primary, the global decision
order below was a tie-breaker choosing between competing leaves. Under
all-applicable it no longer arbitrates — but it still matters for
`propagated_failure` attribution (which step is root vs. downstream) and for the
confusable-pair guidance that keeps annotators from applying near-synonymous leaves
inconsistently. Keep it; reframe it as disambiguation guidance rather than a
selection funnel.

### Global decision order (apply before leaf-specific rules)

1. Same action repeated ≥3× without eval state change → **Action Looping**
   (unless propagated from earlier).
2. Relational instruction, landmark correct in CoT, click violates the relation →
   **Spatial Reasoning Error**.
3. CoT names target T, click near T but outside bbox (within ~1.5× element size) →
   **Click Region Error**.
4. CoT names target T, click far from T and not near any plausible target →
   **Location Hallucination**.
5. Goal understood but hidden affordance never attempted → **Hidden Operation
   Blindness**.
6. Otherwise → leaf-specific rules, or VLM judge with screenshot + CoT.

### Controlled-track gating

These leaves may **only** be assigned when the task carries the matching tag —
otherwise you get false positives from tasks that never exercised the mode:

| Leaf | Required tag |
|---|---|
| Resolution/Scale Brittleness | `zoom_stress` |
| Instruction Ambiguity Failure | `underspecified` |
| Refusal/Infeasibility Error | `infeasible` |
| Fine-Grained Manipulation Failure | `fine_manipulation` |
| Cross-Application Context Loss | `cross_app` |
| Spatial Reasoning Error (primary) | `relational` |

Per-leaf necessary/exclude/confused-with rules are in
`errorAnalysis/failureTaxonomy.md` — the compendium does not duplicate them
because that file is the frozen artifact and must stay the single source.

## Open taxonomy questions

- **How should modes be prioritized?** Raised in the Abdoul+Raghav session, unresolved.
  Candidates: step of occurrence (earlier = more important); impact (how many
  downstream failures trace back to it); or a deliberately designed prioritization
  function.
- **Visual State Misunderstanding** — deferred; revisit only if pilot labeling
  shows a systematic gap.
- **Context Saturation Latency** and **Evaluator Bypass (false positives —
  "succeeds" via a nonsensical or destructive GUI path)** were proposed in the
  stress-testing plan as uncovered modes. Neither is in any taxonomy version.
  Evaluator Bypass is the more interesting one: it is the mirror image of
  `evaluator_mismatch` and nothing currently catches it.
