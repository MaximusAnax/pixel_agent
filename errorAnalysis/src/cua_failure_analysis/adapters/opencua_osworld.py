"""OpenCUA OSWorld-Verified HF trajectory adapter."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cua_failure_analysis.adapters.base import AdapterResult, EpisodeBundle
from cua_failure_analysis.osworld.eval_bundle import format_eval_bundle
from cua_failure_analysis.osworld.grounding import compare_proposed_vs_executed
from cua_failure_analysis.osworld.human_ref import load_human_reference
from cua_failure_analysis.osworld.metadata import load_sources, task_lookup
from cua_failure_analysis.trace.schema import RunManifest, TraceStep

STEP_HEADER_RE = re.compile(r"^#\s*Step\s+(\d+)\s*:", re.M | re.I)
THOUGHT_RE = re.compile(r"##\s*Thought:\s*(.*?)(?=##\s*(?:Action|Code):|\Z)", re.S | re.I)
ACTION_SECTION_RE = re.compile(r"##\s*Action:\s*(.*?)(?=##\s*Code:|\Z)", re.S | re.I)
CODE_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.S | re.I)
CLICK_RE = re.compile(
  r"pyautogui\.click\s*\(\s*(?:x\s*=\s*)?([0-9.]+)\s*,\s*(?:y\s*=\s*)?([0-9.]+)\s*\)",
  re.I,
)
MOVE_RE = re.compile(
  r"pyautogui\.moveTo\s*\(\s*(?:x\s*=\s*)?([0-9.]+)\s*,\s*(?:y\s*=\s*)?([0-9.]+)\s*\)",
  re.I,
)
STEP_SCREENSHOT_RE = re.compile(r"^step_(\d+)_", re.I)

_STRATIFIED_CACHE: dict[str, list[str]] | None = None


def _load_task_tags(task_id: str, stratified_path: Path | None) -> list[str]:
  global _STRATIFIED_CACHE
  if stratified_path is None:
    default = Path(__file__).resolve().parents[3] / "config" / "stratified_tasks.json"
    stratified_path = default if default.exists() else None
  if stratified_path is None or not stratified_path.exists():
    return []

  if _STRATIFIED_CACHE is None:
    data = json.loads(stratified_path.read_text(encoding="utf-8"))
    _STRATIFIED_CACHE = {
      row["task_id"]: list(row.get("task_tags") or [])
      for row in data.get("tasks", [])
      if row.get("task_id")
    }
  return list(_STRATIFIED_CACHE.get(task_id, []))


def _parse_result_txt(path: Path | None) -> bool | None:
  if path is None or not path.exists():
    return None
  raw = path.read_text(encoding="utf-8", errors="replace").strip()
  if not raw:
    return None
  try:
    value = float(raw)
    return value >= 1.0
  except ValueError:
    lower = raw.lower()
    if lower in {"success", "passed", "pass", "true", "1"}:
      return True
    if lower in {"failure", "failed", "fail", "false", "0"}:
      return False
  return None


def _extract_instruction(response: str, instruction_path: Path | None) -> str:
  if instruction_path and instruction_path.exists():
    text = instruction_path.read_text(encoding="utf-8", errors="replace").strip()
    if text:
      return text
  thought = _parse_thought(response)
  if not thought:
    return ""
  for pattern in (
    r"(?:The goal|Our goal|goal)\s+(?:states|is|was)\s+(?:that\s+)?(.+?)(?:\.|Looking at|\n)",
    r"(?:task|instruction)\s+(?:is|was)\s+(?:to\s+)?(.+?)(?:\.|Looking at|\n)",
  ):
    match = re.search(pattern, thought, re.I | re.S)
    if match:
      return match.group(1).strip()[:500]
  return ""


def _parse_thought(response: str) -> str:
  match = THOUGHT_RE.search(response or "")
  return match.group(1).strip() if match else ""


def _parse_action_type(action_raw: str) -> str:
  lower = action_raw.lower()
  if action_raw.strip().upper() == "DONE":
    return "done"
  if "dragto" in lower or "drag(" in lower:
    return "drag"
  if "scroll" in lower:
    return "scroll"
  if "write" in lower or "typewrite" in lower:
    return "type"
  if "hotkey" in lower or "press" in lower:
    return "key"
  if "click" in lower:
    return "click"
  if "moveto" in lower:
    return "move"
  return "other"


def _extract_coords(action_raw: str) -> list[float] | None:
  if not action_raw or action_raw.strip().upper() == "DONE":
    return None
  for pattern in (CLICK_RE, MOVE_RE):
    match = pattern.search(action_raw)
    if match:
      return [float(match.group(1)), float(match.group(2))]
  return None


def _extract_model_code(response: str) -> str:
  match = CODE_BLOCK_RE.search(response or "")
  return match.group(1).strip() if match else ""


def _load_osworld_context(task_id: str, domain: str | None) -> dict:
  """Best-effort load of vendored task/human metadata; empty dict if unavailable."""
  try:
    sources = load_sources()
    task = task_lookup(task_id, domain=domain, sources=sources)
  except (FileNotFoundError, OSError, ValueError, KeyError):
    return {}
  human_actions: list[str] = []
  human_grouped: list[list[str]] = []
  try:
    ref = load_human_reference(task_id, domain=task.get("_domain") or domain, sources=sources)
    human_actions = list(ref.single_action)
    human_grouped = list(ref.grouped_action)
  except (FileNotFoundError, OSError, ValueError, KeyError):
    pass
  return {
    "task": task,
    "sources": sources,
    "canonical_instruction": str(task.get("instruction") or ""),
    "osworld_task_path": str(task.get("_osworld_task_path") or ""),
    "domain": str(task.get("_domain") or domain or ""),
    "human_reference_actions": human_actions,
    "human_reference_grouped": human_grouped,
  }


def _build_screenshot_index(bundle: EpisodeBundle) -> dict[int, str]:
  index: dict[int, str] = {}
  for member in bundle.image_members:
    name = Path(member).name
    match = STEP_SCREENSHOT_RE.match(name)
    if match:
      index[int(match.group(1))] = member
  return index


def _state_hash(step_num: int, action_raw: str, screenshot: str | None) -> str:
  payload = f"{step_num}|{action_raw}|{screenshot or ''}"
  return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _read_traj_records(traj_path: Path) -> list[dict]:
  records: list[dict] = []
  for line in traj_path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line:
      continue
    records.append(json.loads(line))
  return records


def _step_number(record: dict, response: str, fallback: int) -> int:
  for key in ("step_num", "step", "step_id", "index"):
    if key in record:
      try:
        return int(record[key])
      except (TypeError, ValueError):
        pass
  header = STEP_HEADER_RE.search(response or "")
  if header:
    return int(header.group(1))
  return fallback


def normalize_opencua_episode(
  bundle: EpisodeBundle,
  extracted_paths: list[Path],
  *,
  model_id: str,
  package: str,
  stratified_path: Path | None = None,
) -> AdapterResult:
  path_by_name = {p.name: p for p in extracted_paths}
  path_by_suffix: dict[str, Path] = {}
  for path in extracted_paths:
    path_by_suffix[path.name] = path
    rel = "/".join(path.parts[-3:]) if len(path.parts) >= 3 else str(path)
    path_by_suffix[rel] = path
    path_by_suffix[str(path)] = path

  traj_path = path_by_name.get("traj.jsonl")
  if traj_path is None:
    for path in extracted_paths:
      if path.name == "traj.jsonl":
        traj_path = path
        break
  if traj_path is None:
    raise ValueError(f"No traj.jsonl found for episode {bundle.episode_id}")

  result_path = path_by_name.get("result.txt")
  instruction_path = path_by_name.get("instruction.txt")
  success = _parse_result_txt(result_path)
  screenshot_index = _build_screenshot_index(bundle)

  records = _read_traj_records(traj_path)
  instruction = ""
  steps: list[TraceStep] = []

  osw_ctx = _load_osworld_context(bundle.task_id, bundle.domain)
  sources = osw_ctx.get("sources")
  screen_w = int(getattr(sources, "screen_width", 1920) or 1920)
  screen_h = int(getattr(sources, "screen_height", 1080) or 1080)
  tolerance = float(getattr(sources, "grounding_mismatch_tolerance", 0.05) or 0.05)
  canonical = str(osw_ctx.get("canonical_instruction") or "")

  eval_bundle = ""
  if osw_ctx.get("task") is not None:
    result_raw: float | None = None
    if result_path and result_path.exists():
      try:
        result_raw = float(result_path.read_text(encoding="utf-8").strip())
      except ValueError:
        result_raw = None
    eval_bundle = format_eval_bundle(
      osw_ctx["task"],
      result_txt=result_raw,
      outcome=("pass" if success else "fail") if success is not None else None,
    )

  for idx, record in enumerate(records):
    response = str(record.get("response") or "")
    action_raw = str(record.get("action") or "").strip()
    step_num = _step_number(record, response, idx + 1)
    thought = _parse_thought(response)
    if not instruction:
      instruction = canonical or _extract_instruction(response, instruction_path)

    screenshot_member = screenshot_index.get(step_num) or str(record.get("screenshot_file") or "")
    if screenshot_member and not screenshot_member.startswith(bundle.episode_id):
      screenshot_member = f"{bundle.episode_id}/{Path(screenshot_member).name}"

    is_terminal = idx == len(records) - 1
    eval_passed: bool | None = None
    if is_terminal and success is not None:
      eval_passed = success

    reward = record.get("reward")
    done = record.get("done")
    eval_signals: dict = {}
    if reward is not None:
      eval_signals["reward"] = reward
    if done is not None:
      eval_signals["done"] = done
    if is_terminal and success is False:
      eval_signals["failed"] = True
    if is_terminal and eval_bundle:
      eval_signals["message"] = eval_bundle

    action_match = ACTION_SECTION_RE.search(response)
    stated_intent = action_match.group(1).strip()[:500] if action_match else ""
    model_code = _extract_model_code(response)
    grounding = compare_proposed_vs_executed(
      model_code,
      action_raw,
      screen_width=screen_w,
      screen_height=screen_h,
      tolerance=tolerance,
    )
    steps.append(
      TraceStep(
        task_id=bundle.task_id,
        seed=0,
        step=step_num,
        screenshot_path=screenshot_member or None,
        action={
          "type": _parse_action_type(action_raw),
          "raw_code": action_raw,
          "model_code": model_code,
          "stated_intent": stated_intent,
          "action_section": stated_intent,  # backward-compatible alias
          "coords_executed": grounding["coords_executed"],
          "coords_model_normalized": grounding["coords_model_normalized"],
          "coords_model_pixels_est": grounding["coords_model_pixels_est"],
          "grounding_mismatch": grounding["grounding_mismatch"],
        },
        coords=_extract_coords(action_raw),
        cot=thought or response[:2000],
        eval_signals=eval_signals,
        a11y_snippet=[],
        task_tags=_load_task_tags(bundle.task_id, stratified_path),
        instruction=instruction,
        eval_passed=eval_passed,
        state_hash=_state_hash(step_num, action_raw, screenshot_member or None),
      )
    )

  # Prefer canonical OSWorld instruction when available.
  display_instruction = canonical or instruction
  if success:
    eval_message = eval_bundle or ""
  else:
    eval_message = eval_bundle or "run_failed"

  manifest = RunManifest(
    task_id=bundle.task_id,
    seed=0,
    model_id=model_id,
    success=bool(success) if success is not None else False,
    total_steps=len(steps),
    instruction=display_instruction,
    task_tags=_load_task_tags(bundle.task_id, stratified_path),
    eval_message=eval_message,
    canonical_instruction=canonical,
    eval_bundle=eval_bundle,
    human_reference_actions=list(osw_ctx.get("human_reference_actions") or []),
    human_reference_grouped=list(osw_ctx.get("human_reference_grouped") or []),
    osworld_task_path=str(osw_ctx.get("osworld_task_path") or ""),
    domain=str(osw_ctx.get("domain") or bundle.domain or ""),
  )
  return AdapterResult(manifest=manifest, steps=steps)


class OpenCuaOsworldAdapter:
  def normalize_episode(
    self,
    bundle: EpisodeBundle,
    extracted_paths: list[Path],
    *,
    model_id: str,
    package: str,
  ) -> AdapterResult:
    return normalize_opencua_episode(
      bundle,
      extracted_paths,
      model_id=model_id,
      package=package,
    )
