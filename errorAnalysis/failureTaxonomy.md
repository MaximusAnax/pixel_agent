The taxonomy of computer-use agent errors can be divided into **Perception/Grounding Errors**, which involve the failure to accurately map instructions to visual UI elements, and **Cognitive/Planning Errors**, which involve failures in high-level reasoning, intent understanding, and memory.

**Perception and Grounding Errors**

These failures occur when an agent cannot correctly identify or interact with the physical properties of the interface.

- **Click Region Error**: The agent conceptually identifies the correct UI element but predicts imprecise or "wrong physical area" coordinates for the interaction.
  - *Example*: An agent is instructed to "Click on 'Done' button" and identifies it in reasoning, but its output coordinates fall outside the button's actual boundary.
- **Visual Confusion (Primitive Reliance)**: The agent relies on superficial visual cues (shape, color, position) rather than functional semantics, mistaking one type of element for another.
  - *Example*: An agent mistakes a light-colored button for a search box because both are white rectangles near the top of the screen.
- **Text Matching Bias**: The agent clicks on visible text that matches a word in the instruction without verifying if that text is actually the interactive target.
  - *Example*: When told to "Click on 'First Name' textbox," the agent clicks the "First Name" text label instead of the actual input field beneath it.
- **Resolution/Scale Brittleness**: A failure to adapt to changes in browser zoom or screen resolution, often because the model has memorized absolute pixel positions.
  - *Example*: In a 70% browser zoom scenario, an agent clicks on the empty space where a button *used* to be at 100% scale, indicating it memorized a position rather than learning a functional target.
- **Fine-Grained Manipulation Failure**: A breakdown in precision when tasks require character-level cursor placement or the adjustment of compact components like sliders.
  - *Example*: An agent fails to place the cursor precisely between the word "person" and the number "1" in a text field, which occupies only a tiny pixel region.
- **Software Commonsense (Icon Recognition) Failure**: The inability to associate visual symbols with their functional purpose without explicit text labels.
  - *Example*: An agent fails to identify a magnifying glass symbol as the "Search" function or a gear icon as "Settings".

**Cognitive and Planning Errors**

These failures stem from the agent's inability to maintain a coherent strategy, interpret user intent, or manage multi-step workflows.

- **Action Looping (Repetition)**: The agent repeats the same unsuccessful action multiple times without adapting to environmental feedback.
  - *Example*: An agent repeatedly types a search term into a field without ever clicking the "Search" button to progress the task.
- **Location Hallucination**: A disconnect where the agent's internal reasoning correctly identifies a target, but it outputs "fabricated" or random coordinates unrelated to that target.
  - *Example*: An agent correctly reasons that the "Notifications" option is in the left sidebar but then outputs coordinates for a completely different area of the screen.
- **Spatial Reasoning Error**: The agent incorrectly interprets relative spatial relationships such as "above," "below," "left," or "right".
  - *Example*: Instructed to "Click on the link to the left of 'Side effects'," the agent identifies the correct landmark but clicks a link on the right instead.
- **Goal Hallucination**: The agent "invents user intent" or sub-goals that were never specified in the original instruction.
  - *Example*: When told to click a heart-shaped icon, the agent assumes the goal is to "save this cooking activity to my favorites" and proceeds based on that unstated assumption.
- **Reasoning Drift**: The process of explicit reasoning (Chain-of-Thought) actually misleads the final action prediction rather than helping it.
  - *Example*: A model reasons that a logo is "located at the bottom" of a section and this self-generated thought misleads it to click an unrelated image at the very bottom of the entire screen.
- **Long-Horizon Memory Failure**: The agent loses track of key information or intermediate sub-goals after a high number of interaction steps.
  - *Example*: In a repetitive workflow like converting 20 files, the agent drifts from the original plan or forgets which files it has already processed after the tenth step.
- **Instruction Ambiguity Failure**: The failure to resolve underspecified queries, leading the agent to take speculative actions that don't match user expectations.
  - *Example*: When told to "Make Times New Roman the default font," the agent changes the font for the *current document* only, while the evaluator expected a *global system setting* change.
- **Refusal/Infeasibility Error**: The failure to recognize when a task is impossible given the current UI state, often resulting in "speculative" clicks on unrelated elements.
  - *Example*: An agent is told to "Open the Firefox browser" on a desktop where no Firefox icon is visible; instead of refusing, it clicks a random unrelated icon.
- **Hidden Operation Blindness**: The agent understands the high-level goal but fails to discover or use affordances that are not directly visible on screen—buried in menus, context menus, ribbons, keyboard shortcuts, or other non-obvious action paths.
  - *Example*: A task requires applying a slide transition in LibreOffice Impress, but the agent repeatedly clicks visible top-level menus instead of opening the right-sidebar tab where transition settings live.
- **Cross-Application Context Loss**: The agent fails to maintain task-relevant state when switching between applications or environments, losing copied data, intermediate results, or sub-goal progress across app boundaries.
  - *Example*: The agent copies output from a terminal but pastes stale clipboard content into a spreadsheet because it lost track of which application holds the current working state.

---

## Labeling policy

### Scope

- Label at the **first failure step** `t*` (earliest step where the run is irrecoverable or evaluator fails).
- Assign exactly **one primary** root-cause leaf per `t*`.
- Optionally assign **secondary** leaves when multiple modes clearly co-occur at the same step.
- Apply meta-label **`propagated_failure`** when the labeled step is a downstream consequence of an error at `t' < t*` (common for Action Looping and Long-Horizon Memory Failure).

### Meta-labels (orthogonal to leaves)

| Meta-label | When to use |
|---|---|
| `evaluator_mismatch` | Action is reasonable per human rubric but OSWorld script marks failure |
| `propagated_failure` | Failure at `t*` caused by earlier root error |

### Global decision order (apply before leaf-specific rules)

1. If same action repeated ≥3 times without eval state change → **Action Looping** (unless `propagated_failure` from earlier step).
2. If instruction uses relative spatial terms ("left of", "above") and landmark is correct in CoT but click is wrong relative to landmark → **Spatial Reasoning Error**.
3. If CoT names target T and click is near T but outside bbox (within ~1.5× element size) → **Click Region Error**.
4. If CoT names target T and click is far from T and not near any plausible target → **Location Hallucination**.
5. If goal is understood but agent never attempts menu/shortcut/sidebar/hidden affordance required by GT → **Hidden Operation Blindness**.
6. Otherwise → apply leaf-specific rules below or VLM judge with screenshot + CoT.

### Controlled-track gating

Only assign these leaves when the matching task tag is set:

| Leaf | Required tag |
|---|---|
| Resolution/Scale Brittleness | `zoom_stress` |
| Instruction Ambiguity Failure | `underspecified` |
| Refusal/Infeasibility Error | `infeasible` |
| Fine-Grained Manipulation Failure | `fine_manipulation` |
| Cross-Application Context Loss | `cross_app` |
| Spatial Reasoning Error (primary) | `relational` (or relational probe set) |

---

## Decision rules by leaf

### Perception and Grounding

#### Click Region Error
- **Necessary:** CoT or action type identifies the correct element; click coordinates miss the element bbox but land within a small margin of it.
- **Exclude if:** CoT names a different element than the one near the click → Visual Confusion, Text Matching, or Location Hallucination.
- **Confused with:** Location Hallucination (click far from target), Fine-Grained Manipulation (sub-element precision).

#### Visual Confusion (Primitive Reliance)
- **Necessary:** Agent selects wrong **element type** based on shape/color/layout similarity (not instruction text match).
- **Exclude if:** Failure is because instruction word appears on a static label → Text Matching Bias.
- **Confused with:** Text Matching Bias, Software Commonsense Failure.

#### Text Matching Bias
- **Necessary:** Click lands on visible text matching an instruction token; target is a different interactive element (input, button).
- **Exclude if:** No instruction-text overlap; wrong element type without text match → Visual Confusion.
- **Confused with:** Visual Confusion, Click Region Error.

#### Resolution/Scale Brittleness
- **Necessary:** Same task fails at non-standard zoom/resolution but succeeds at default in paired runs; click targets memorized absolute positions.
- **Exclude if:** Only one zoom level tested.
- **Confused with:** Click Region Error, Location Hallucination.

#### Fine-Grained Manipulation Failure
- **Necessary:** Task requires sub-element precision (cursor between characters, slider notch); coarse click is in the right widget but wrong offset.
- **Exclude if:** Wrong widget entirely → other perception leaves.
- **Confused with:** Click Region Error.

#### Software Commonsense (Icon Recognition) Failure
- **Necessary:** Task requires recognizing icon/symbol function without text label; agent fails to map symbol to action.
- **Exclude if:** Text-labeled control was available and ignored → Text Matching or Hidden Operation Blindness.
- **Confused with:** Hidden Operation Blindness (icon in toolbar vs buried in menu).

### Cognitive and Planning

#### Action Looping (Repetition)
- **Necessary:** ≥3 contiguous identical or equivalent actions without progress.
- **Exclude if:** Root cause is earlier single mis-click → mark primary at `t'` and `propagated_failure` at loop step.
- **Confused with:** Long-Horizon Memory Failure, Hidden Operation Blindness.

#### Location Hallucination
- **Necessary:** CoT identifies target T; output coordinates are unrelated to T (not a near-miss).
- **Exclude if:** Click is near T but outside bbox → Click Region Error.
- **Confused with:** Click Region Error, Reasoning Drift.

#### Spatial Reasoning Error
- **Necessary:** Relational instruction; landmark identified correctly; click violates stated relation.
- **Exclude if:** Wrong landmark in CoT → Visual Confusion or Goal Hallucination.
- **Confused with:** Click Region Error (when landmark is wrong).

#### Goal Hallucination
- **Necessary:** Agent pursues sub-goal or intent **not entailed** by the instruction.
- **Exclude if:** Instruction is underspecified and multiple valid interpretations exist → Instruction Ambiguity Failure.
- **Confused with:** Instruction Ambiguity Failure, Reasoning Drift.

#### Reasoning Drift
- **Necessary:** CoT contains a false claim about layout/state that **directly misleads** the action; instruction interpretation is otherwise correct.
- **Exclude if:** CoT is correct but coords wrong → Location Hallucination or Click Region Error.
- **Confused with:** Goal Hallucination, Visual Confusion.

#### Long-Horizon Memory Failure
- **Necessary:** Failure after many steps; agent forgets progress, file list, or sub-goal stated earlier in trace.
- **Exclude if:** Failure at step ≤3 → prefer perception/planning leaves at `t*`.
- **Confused with:** Action Looping (often propagated), Cross-Application Context Loss.

#### Instruction Ambiguity Failure
- **Necessary:** Task is underspecified; agent picks a plausible but evaluator-rejected interpretation.
- **Exclude if:** Instruction is clear; agent invents extra goals → Goal Hallucination.
- **Confused with:** Goal Hallucination, `evaluator_mismatch`.

#### Refusal/Infeasibility Error
- **Necessary:** Task impossible in current UI; agent should CALL_USER/terminate but instead clicks randomly or loops.
- **Exclude if:** Task is feasible but hard → Hidden Operation Blindness or other leaves.
- **Confused with:** Action Looping, Hidden Operation Blindness.

#### Hidden Operation Blindness
- **Necessary:** High-level goal correct in CoT; agent only tries visible/salient controls; GT requires menu, shortcut, context menu, or sidebar tab.
- **Exclude if:** Agent never understood goal → Goal Hallucination or Reasoning Drift.
- **Confused with:** Software Commonsense Failure, Refusal/Infeasibility Error.

#### Cross-Application Context Loss
- **Necessary:** Failure occurs at or after app switch; agent loses clipboard, file handle, or cross-app state.
- **Exclude if:** Single-app task → other leaves.
- **Confused with:** Long-Horizon Memory Failure.

