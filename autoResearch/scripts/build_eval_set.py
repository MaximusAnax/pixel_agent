#!/usr/bin/env python3
"""Build the frozen fixture eval set (deterministic; run only deliberately).

These are SYNTHETIC harness-validation fixtures, not scientific data (see
data/eval_set/README.md). Cases are designed so the baseline detector config
mislabels some of them in ways a candidate search can genuinely fix, with
holdout twins confirming the fix generalizes:

  - looping-two-reps(+h): 2 identical clicks; baseline min_repeat=3 misses.
  - click-medium-miss(+h): ~45-50px miss; between near-margin and far
    thresholds at baseline, so unresolved. Wider near_margin_ratio fixes it;
    shrinking far_threshold_px instead mislabels it Location Hallucination.
  - long-horizon-trap-h: mid-trace failure the baseline long-horizon
    heuristic false-positives on; a higher threshold_ratio drops the FP
    while keeping the true late-step case.
  - goal-halluc / hidden-op / multi-label: judge-only leaves — the detector
    executor's ceiling stays visibly below 1.0.

Rebuilding rewrites data/eval_set and its content hash. That is a HUMAN
decision — the loop must never call this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "errorAnalysis" / "src"))

from auto_research.objective import _hash_eval_content  # noqa: E402

EVAL_ROOT = ROOT / "data" / "eval_set"

DONE_BTN = {"role": "button", "name": "Done", "bbox": [200, 100, 240, 130], "interactive": True}
EMAIL_LABEL = {"role": "text", "name": "Email", "bbox": [50, 200, 110, 220], "interactive": False}
LOGO = {"role": "image", "name": "logo", "bbox": [400, 40, 460, 80], "interactive": False}


def step(task_id, n, action, coords=None, cot="", a11y=(), tags=(), instr="",
         eval_passed=None, signals=None, state="s0"):
  return {
    "task_id": task_id,
    "seed": 0,
    "step": n,
    "screenshot_path": None,
    "action": action,
    "coords": coords,
    "cot": cot,
    "eval_signals": signals or {},
    "a11y_snippet": list(a11y),
    "task_tags": list(tags),
    "instruction": instr,
    "eval_passed": eval_passed,
    "state_hash": state,
  }


def click(x, y):
  return {"type": "click"}, [float(x), float(y)]


def build_cases() -> list[dict]:
  cases = []

  def add(case_id, split, gold, steps, instruction, tags=(), reference="", score=0.0,
          eval_output="evaluator: target state not reached"):
    cases.append(
      {
        "case_id": case_id,
        "split": split,
        "gold_modes": sorted(gold),
        "instruction": instruction,
        "task_tags": list(tags),
        "reference_summary": reference or "human: 2 steps — click Done, verify toast",
        "osworld_score": score,
        "eval_output": eval_output,
        "steps": steps,
      }
    )

  def looping_steps(task, n_reps, prefix_steps=()):
    steps = list(prefix_steps)
    base = len(steps)
    act, coords = click(220, 115)  # inside Done bbox
    for i in range(n_reps):
      last = i == n_reps - 1
      steps.append(
        step(task, base + i + 1, act, coords, "I will click the Done button.",
             [DONE_BTN], instr="Click Done to save",
             eval_passed=False if last else None,
             signals={"failed": True} if last else None)
      )
    return steps

  # 1-2. Clear 3-rep loops (baseline catches).
  add("looping-clear", "calibration", ["Action Looping (Repetition)"],
      looping_steps("looping-clear", 3), "Click Done to save")
  add("looping-clear-b", "calibration", ["Action Looping (Repetition)"],
      looping_steps("looping-clear-b", 4), "Click Done to save")

  # 3-4. Two-rep loops: baseline min_repeat=3 misses; min_repeat=2 fixes.
  two_rep_prefix = [
    step("looping-two-reps", 1, {"type": "type", "text": "report"}, None,
         "Type the filename first.", [DONE_BTN], instr="Click Done to save"),
  ]
  add("looping-two-reps", "calibration", ["Action Looping (Repetition)"],
      looping_steps("looping-two-reps", 2, two_rep_prefix), "Click Done to save")
  two_rep_prefix_h = [
    step("looping-two-reps-h", 1, {"type": "scroll", "text": None}, None,
         "Scroll to the button.", [DONE_BTN], instr="Click Done to save"),
  ]
  add("looping-two-reps-h", "holdout", ["Action Looping (Repetition)"],
      looping_steps("looping-two-reps-h", 2, two_rep_prefix_h), "Click Done to save")

  # 5. Near miss just outside bbox (~8px): baseline catches (margin 15px).
  act, coords = click(220, 138)  # 8px below Done bbox bottom
  add("click-near-miss", "calibration", ["Click Region Error"],
      [step("click-near-miss", 1, act, coords, "Click the Done button to submit.",
            [DONE_BTN], instr="Submit the form with Done", eval_passed=False,
            signals={"failed": True})],
      "Submit the form with Done")

  # 6-7. Medium miss (~45-50px): baseline unresolved. near_margin_ratio=5.0
  # fixes; far_threshold_px=40 would flip it to Location Hallucination (wrong).
  act, coords = click(220, 180)  # 50px below bbox
  add("click-medium-miss", "calibration", ["Click Region Error"],
      [step("click-medium-miss", 1, act, coords, "Click Done to finish setup.",
            [DONE_BTN], instr="Finish setup by pressing Done", eval_passed=False,
            signals={"failed": True})],
      "Finish setup by pressing Done")
  act, coords = click(220, 175)  # 45px below bbox
  add("click-medium-miss-h", "holdout", ["Click Region Error"],
      [step("click-medium-miss-h", 1, act, coords, "Press Done to continue.",
            [DONE_BTN], instr="Press Done to continue", eval_passed=False,
            signals={"failed": True})],
      "Press Done to continue")

  # 8-9. Far misses (250-300px): Location Hallucination at any grid far value.
  act, coords = click(700, 400)
  add("location-halluc", "calibration", ["Location Hallucination"],
      [step("location-halluc", 1, act, coords, "Clicking the Done button now.",
            [DONE_BTN], instr="Click Done", eval_passed=False, signals={"failed": True})],
      "Click Done")
  act, coords = click(650, 360)
  add("location-halluc-h", "holdout", ["Location Hallucination"],
      [step("location-halluc-h", 1, act, coords, "I see the Done button; clicking it.",
            [DONE_BTN], instr="Click Done", eval_passed=False, signals={"failed": True})],
      "Click Done")

  # 10. Text-matching bias: click lands on the non-interactive "Email" label.
  act, coords = click(80, 210)
  add("text-match-label", "calibration", ["Text Matching Bias"],
      [step("text-match-label", 1, act, coords, "Click the Email field to focus it.",
            [EMAIL_LABEL], instr="Enter your email address", eval_passed=False,
            signals={"failed": True})],
      "Enter your email address")

  # 11. Spatial (tag-gated): relational instruction, landmark in CoT.
  act, coords = click(480, 60)  # right of logo though instruction says left
  add("spatial-relational", "calibration", ["Spatial Reasoning Error"],
      [step("spatial-relational", 1, act, coords,
            "The button is next to the logo; clicking there.",
            [LOGO], ["relational"], "Click the button to the left of the logo",
            eval_passed=False, signals={"failed": True})],
      "Click the button to the left of the logo", tags=["relational"])

  # 12. True long-horizon: failure at the final step (12/12).
  lh_steps = []
  for i in range(1, 13):
    if i < 10:
      a, c = {"type": "scroll"}, None
      cot = f"Working through part {i} of the batch."
    elif i < 12:
      a, c = {"type": "type", "text": f"file-{i}"}, None
      cot = f"Renaming file {i}."
    else:
      a, c = click(220, 115)
      cot = "Re-doing the rename for file 3 — I lost track of progress."
    lh_steps.append(
      step("long-horizon", i, a, c, cot, [DONE_BTN], instr="Rename all 10 files",
           eval_passed=False if i == 12 else None,
           signals={"failed": True} if i == 12 else None, state=f"s{i}")
    )
  add("long-horizon", "calibration", ["Long-Horizon Memory Failure"], lh_steps,
      "Rename all 10 files")

  # 13. Long-horizon trap (holdout): failure at step 9/12, gold is a judge-only
  # leaf. Baseline threshold_ratio=0.7 false-positives Long-Horizon here;
  # 0.95 drops the FP and still catches case 12.
  trap_steps = []
  for i in range(1, 13):
    a, c = ({"type": "scroll"}, None) if i % 2 else ({"type": "type", "text": f"q{i}"}, None)
    cot = f"Continuing setup step {i}."
    if i == 9:
      cot = "I'll also enable dark mode since the user probably wants it."
      a, c = click(220, 115)
    trap_steps.append(
      step("long-horizon-trap-h", i, a, c, cot, [DONE_BTN],
           instr="Install the extension", eval_passed=False if i == 9 else None,
           signals={"failed": True} if i == 9 else None, state=f"s{i}")
    )
  add("long-horizon-trap-h", "holdout", ["Goal Hallucination"], trap_steps,
      "Install the extension")

  # 13b. Calibration twin of the trap, so threshold_ratio is learnable from
  # the calibration split (holdout confirms, never drives).
  trap_cal = []
  for i in range(1, 13):
    a, c = ({"type": "scroll"}, None) if i % 2 else ({"type": "type", "text": f"w{i}"}, None)
    cot = f"Filling in section {i} of the form."
    if i == 9:
      cot = "I'll add a profile photo too — forms look better complete."
      a, c = click(220, 115)
    trap_cal.append(
      step("long-horizon-trap", i, a, c, cot, [DONE_BTN],
           instr="Submit the request form", eval_passed=False if i == 9 else None,
           signals={"failed": True} if i == 9 else None, state=f"s{i}")
    )
  add("long-horizon-trap", "calibration", ["Goal Hallucination"], trap_cal,
      "Submit the request form")

  # 14. Judge-only leaves: detectors cannot reach these.
  act, coords = click(220, 115)
  add("goal-halluc", "calibration", ["Goal Hallucination"],
      [step("goal-halluc", 1, act, coords,
            "I'll first create a backup folder — safer that way.",
            [DONE_BTN], instr="Delete the temp folder", eval_passed=False,
            signals={"failed": True})],
      "Delete the temp folder")
  add("hidden-op", "holdout", ["Hidden Operation Blindness"],
      [step("hidden-op", 1, {"type": "scroll"}, None,
            "Scrolling the main menu to find the export option.",
            [DONE_BTN], instr="Export via the right-side panel", eval_passed=False,
            signals={"failed": True})],
      "Export via the right-side panel")

  # 15. Multi-label: 3-rep loop whose repeated click is ALSO a near-miss.
  ml_steps = []
  act, coords = click(220, 138)  # 8px outside bbox
  for i in range(1, 4):
    ml_steps.append(
      step("multi-label", i, act, coords, "Click the Done button.",
           [DONE_BTN], instr="Click Done to save", eval_passed=False if i == 3 else None,
           signals={"failed": True} if i == 3 else None)
    )
  add("multi-label", "calibration",
      ["Action Looping (Repetition)", "Click Region Error"], ml_steps,
      "Click Done to save")

  return cases


def main() -> None:
  cases = build_cases()
  traces_root = EVAL_ROOT / "traces"
  manifest_cases = []
  for case in cases:
    case_dir = traces_root / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    trace_path = case_dir / "trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
      for s in case["steps"]:
        f.write(json.dumps(s, sort_keys=True) + "\n")
    (case_dir / "manifest.json").write_text(
      json.dumps(
        {
          "task_id": case["case_id"],
          "seed": 0,
          "model_id": "fixture",
          "success": False,
          "total_steps": len(case["steps"]),
          "instruction": case["instruction"],
          "task_tags": case["task_tags"],
          "eval_message": case["eval_output"],
        },
        indent=2,
        sort_keys=True,
      ),
      encoding="utf-8",
    )
    manifest_cases.append(
      {
        "case_id": case["case_id"],
        "split": case["split"],
        "trace": f"traces/{case['case_id']}/trace.jsonl",
        "gold_modes": case["gold_modes"],
        "instruction": case["instruction"],
        "task_tags": case["task_tags"],
        "reference_summary": case["reference_summary"],
        "osworld_score": case["osworld_score"],
        "eval_output": case["eval_output"],
      }
    )

  manifest = {
    "version": 1,
    "provenance": "synthetic fixtures — see README.md; NOT scientific data",
    "cases": manifest_cases,
  }
  manifest["content_hash"] = _hash_eval_content(manifest, EVAL_ROOT)
  (EVAL_ROOT / "eval_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
  )
  n_cal = sum(1 for c in manifest_cases if c["split"] == "calibration")
  n_hold = len(manifest_cases) - n_cal
  print(
    f"Wrote {len(manifest_cases)} cases ({n_cal} calibration / {n_hold} holdout) "
    f"to {EVAL_ROOT}\ncontent_hash={manifest['content_hash']}"
  )


if __name__ == "__main__":
  main()
