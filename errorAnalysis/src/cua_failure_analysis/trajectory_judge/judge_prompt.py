"""Build the VLM-judge chat messages for one (failed) trajectory.

Operates on the *normalized* trajectory record produced by `parse_trajs.py`:

    {
      "model": str, "domain": str, "task_id": str,
      "instruction": str, "reward": float, "num_steps": int,
      "steps": [{"idx": int, "screenshot_path": str|None,
                 "reasoning": str, "action": str}, ...]
    }

The text log includes *every* step; only a sampled subset of screenshots is
attached as images (image budget), since trajectories can be 50+ steps.
"""

from __future__ import annotations

from cua_failure_analysis.trajectory_judge.taxonomy import render_taxonomy

SYSTEM_PROMPT = f"""You are an expert analyst of computer-use agent (CUA) failures. \
A CUA is a vision-language model that controls a Ubuntu desktop by looking at \
screenshots and issuing pyautogui actions (clicks with x,y coordinates, typing, \
hotkeys, scrolls) to complete a natural-language task. You are given a trajectory \
that the OSWorld benchmark's automated checker scored as FAILED (reward 0.0).

TAXONOMY OF FAILURE MODES:
{render_taxonomy()}

DECISION PROCEDURE (follow in order):
1. Read the instruction and the step log. Determine what the task required and what \
the agent actually did.
2. Find the step where the trajectory FIRST clearly went wrong (not just the last \
step). The reward is 0.0, so SOMETHING went wrong even if the run looks plausible.
3. Decide the CATEGORY first:
   - perception_grounding: the agent's reasoning named the correct target/intent, \
but it failed at the visual/physical level — coordinates landed off the element, it \
confused one widget for another, misread an icon, or fumbled fine manipulation.
   - cognitive_planning: the agent's reasoning, intent, memory, or strategy itself \
was wrong — it looped, invented goals, lost track over many steps, misjudged \
spatial relations, or kept trying an impossible task.
   - other: nothing fits, OR the run genuinely looks correct/complete (likely an \
evaluator or environment issue), OR the trajectory is too truncated to judge.
4. Pick the single most specific mode WITHIN that category.

WRITING THE ANALYSIS:
- Describe what THIS specific agent did, citing concrete step numbers, the actual \
elements/coordinates involved, and what you see in the screenshots. Do NOT restate \
the generic taxonomy definitions — a generic analysis is unacceptable.

CRITICAL RULES:
- Your label must MATCH your analysis. If your analysis concludes the agent \
misunderstood the task or got stuck, the mode must be a cognitive_planning mode — \
NOT click_region_error.
- Do NOT default to click_region_error. Only choose it when you can actually SEE in \
a screenshot that the agent aimed at a correctly-identified element but its x,y fell \
outside that element's boundary. A wrong click caused by misunderstanding is \
cognitive, not click_region_error.
- action_looping requires the SAME (or near-identical) action to be REPEATED several \
times with no progress. Do NOT use it for a single premature stop or a run that \
simply didn't finish.
- If the agent stopped early — e.g. its action is 'DONE'/'FAIL'/'WAIT' or it \
declares the task complete/impossible — before the task was actually satisfied, that \
is refusal_infeasibility_error (or goal_hallucination / instruction_ambiguity_failure \
if it misread intent). Not action_looping, not a perception mode.
- If the agent used all/most of its step budget without completing, identify WHY \
(genuine action_looping with repetition, long_horizon_memory_failure, or a wrong \
strategy).
- A reward-0.0 run often looks superficially complete because you cannot see the \
final automated check. Do NOT jump to 'other'. First look hard for the subtle \
mistake: did the agent skip a sub-requirement, use a wrong value/format/scope, act \
on the wrong file or object, or stop one action short of the confirming click/save? \
Then commit to the MOST LIKELY specific mode with a calibrated confidence. Reserve \
'other' for runs that are truly indistinguishable from success or are clearly \
environment/harness failures (crash, timeout) — 'other' should be UNCOMMON.
- Calibrate confidence: high (>0.8) only when the mistake is clearly visible; \
0.4-0.7 when the mode is your best inference but you are uncertain; low (<0.4) only \
for genuine 'other'.

Output ONLY a JSON object matching the provided schema. Choose ONE primary mode; \
list secondary modes only if they genuinely contributed."""


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\r", " ")
    if len(text) > limit:
        return text[:limit] + " …[truncated]"
    return text


def build_step_log(traj: dict, reason_chars: int = 600, action_chars: int = 300,
                   max_steps: int = 45, head: int = 12) -> str:
    """Compact textual log of steps (reasoning + action). For very long
    trajectories, keep the first `head` and last `max_steps-head` steps and elide
    the middle (the full log would otherwise overflow the context window)."""
    steps = traj["steps"]
    elided = None
    if len(steps) > max_steps:
        tail = max_steps - head
        elided = (steps[head]["idx"], steps[-tail - 1]["idx"])
        steps = steps[:head] + steps[-tail:]

    lines: list[str] = []
    for s in steps:
        idx = s["idx"]
        if elided and idx == steps[head]["idx"] and head < len(traj["steps"]):
            lines.append(f"\n... [steps {elided[0]}–{elided[1]} omitted for length] ...\n")
        reasoning = _truncate(s.get("reasoning", ""), reason_chars)
        action = _truncate(s.get("action", ""), action_chars)
        has_img = " [screenshot attached below]" if s.get("_attached") else ""
        lines.append(f"--- Step {idx}{has_img} ---")
        if reasoning:
            lines.append(f"REASONING: {reasoning}")
        lines.append(f"ACTION: {action if action else '(none recorded)'}")
    return "\n".join(lines)


def select_screenshot_steps(traj: dict, max_images: int = 10) -> list[int]:
    """Pick which steps' screenshots to attach: the earliest step, the last few
    steps (where failure manifests), and evenly-spaced keyframes in between.
    Each attached shot is the POST-action state of that step (see build_messages)."""
    with_img = [s["idx"] for s in traj["steps"] if s.get("screenshot_path")]
    if not with_img:
        return []
    if len(with_img) <= max_images:
        return with_img

    chosen: set[int] = set()
    chosen.add(with_img[0])              # earliest captured state
    for i in with_img[-4:]:              # last 4 (failure usually visible here)
        chosen.add(i)
    remaining = max_images - len(chosen)
    middle = [i for i in with_img if i not in chosen]
    if remaining > 0 and middle:
        step = max(1, len(middle) // (remaining + 1))
        for k in range(remaining):
            j = min((k + 1) * step, len(middle) - 1)
            chosen.add(middle[j])
    return sorted(chosen)


def build_messages(traj: dict, selected_steps: list[int]) -> list[dict]:
    """Return chat messages with {"type":"image"} placeholders (one per selected
    step, in order). The caller supplies the actual PIL images in the SAME order
    via vLLM multi_modal_data."""
    sel = set(selected_steps)
    for s in traj["steps"]:
        s["_attached"] = s["idx"] in sel

    header = (
        f"TASK INSTRUCTION:\n{traj['instruction']}\n\n"
        f"DOMAIN: {traj['domain']}    AGENT MODEL: {traj['model']}\n"
        f"OUTCOME: OSWorld reward = {traj['reward']} (FAILED). "
        f"Total steps taken: {traj['num_steps']}.\n\n"
        f"FULL STEP-BY-STEP ACTION LOG (all {traj['num_steps']} steps):\n"
        f"{build_step_log(traj)}\n"
    )

    content: list[dict] = [{"type": "text", "text": header}]
    if selected_steps:
        content.append({
            "type": "text",
            "text": (
                f"\nSCREENSHOTS for {len(selected_steps)} selected steps are shown "
                "below in order. TIMING (important): the screenshot labeled 'step k' "
                "is the desktop AFTER step k's action executed — i.e. the RESULT of "
                "that action (and the state the agent then observed before choosing "
                "step k+1). There is no separate pre-action screenshot for step 1; "
                "the very first state was not saved. So read 'step k' as the "
                "consequence of action k: if action k was a click, this screenshot "
                "shows where the UI ended up after that click — your main evidence "
                "for whether it had the intended effect. To see what the agent was "
                "looking at when it CHOSE action k, use the previous attached "
                "screenshot ('step k-1') when one is present."
            ),
        })
        for idx in selected_steps:
            content.append({"type": "text", "text": f"\n[Screenshot — step {idx}]"})
            content.append({"type": "image"})
    else:
        content.append({"type": "text", "text": "\n(No screenshots were available for this trajectory.)"})

    content.append({
        "type": "text",
        "text": "\nNow output the JSON classification of the dominant failure mode.",
    })

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
