"""OpenCUA OSWorld-Verified HF trajectory adapter."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cua_failure_analysis.adapters.base import AdapterResult, EpisodeBundle
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

  for idx, record in enumerate(records):
    response = str(record.get("response") or "")
    action_raw = str(record.get("action") or "").strip()
    step_num = _step_number(record, response, idx + 1)
    thought = _parse_thought(response)
    if not instruction:
      instruction = _extract_instruction(response, instruction_path)

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

    action_match = ACTION_SECTION_RE.search(response)
    steps.append(
      TraceStep(
        task_id=bundle.task_id,
        seed=0,
        step=step_num,
        screenshot_path=screenshot_member or None,
        action={
          "type": _parse_action_type(action_raw),
          "raw_code": action_raw,
          "action_section": action_match.group(1).strip()[:500] if action_match else "",
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

  manifest = RunManifest(
    task_id=bundle.task_id,
    seed=0,
    model_id=model_id,
    success=bool(success) if success is not None else False,
    total_steps=len(steps),
    instruction=instruction,
    task_tags=_load_task_tags(bundle.task_id, stratified_path),
    eval_message="" if success else "run_failed",
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
