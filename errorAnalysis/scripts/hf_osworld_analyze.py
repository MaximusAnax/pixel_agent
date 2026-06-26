#!/usr/bin/env python3
"""Remote HF OSWorld-Verified trajectory analyzer.

This script is intentionally conservative:
- it runs on Babel, not on the laptop;
- it downloads at most one selected zip package;
- it extracts bounded episode samples into job work storage;
- it writes compact analysis artifacts that can be synced home.

The OSWorld-Verified repository is zip-based and may change its internal file
layout over time. The adapter therefore starts with an inventory and a
best-effort normalizer. If a package layout is unknown, the run still produces
an actionable `adapter_gaps.json` instead of silently failing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cua_failure_analysis.adapters import (
  EpisodeBundle,
  get_adapter,
  group_opencua_episodes,
  uses_opencua_grouping,
)
from cua_failure_analysis.adapters.screenshots import extract_screenshot_for_judge
from cua_failure_analysis.attribution.first_failure import find_first_failure_step
from cua_failure_analysis.attribution.pipeline import attribute_run
from cua_failure_analysis.judge.anthropic_client import AnthropicJudge, AnthropicJudgeConfig
from cua_failure_analysis.judge.client import VLMJudge, VLMJudgeConfig
from cua_failure_analysis.judge.protocol import JudgeClient
from cua_failure_analysis.judge.usage import log_judge_usage, summarize_judge_usage
from cua_failure_analysis.trace.schema import RunManifest, TraceStep, load_trace


REASONING_KEYS = (
  "cot",
  "thought",
  "thinking",
  "reasoning",
  "rationale",
  "response",
  "model_response",
  "message",
  "content",
)
ACTION_KEYS = (
  "action",
  "actions",
  "operation",
  "pyautogui_code",
  "computer_action",
  "prediction",
)
SUCCESS_KEYS = ("success", "passed", "eval_passed", "score", "result")


@dataclass
class EpisodeCandidate:
  episode_id: str
  members: list[str]
  json_members: list[str]
  text_members: list[str]
  image_members: list[str]
  result_members: list[str]


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Analyze one HF OSWorld trajectory zip")
  parser.add_argument("--repo-id", default="xlangai/ubuntu_osworld_verified_trajs")
  parser.add_argument("--revision", default="main")
  parser.add_argument("--package", required=True, help="Zip filename in the HF dataset repo")
  parser.add_argument("--raw-root", type=Path, required=True)
  parser.add_argument("--shared-datasets-root", type=Path, default=Path("/data/datasets"))
  parser.add_argument("--work-root", type=Path, required=True)
  parser.add_argument("--output-dir", type=Path, required=True)
  parser.add_argument("--max-episodes", type=int, default=25)
  parser.add_argument(
    "--phase",
    choices=("pilot", "core", "all"),
    default=os.environ.get("OSWORLD_PHASE", "all"),
    help="Restrict episodes to the pre-registered pilot (30) or core (100) task IDs.",
  )
  parser.add_argument(
    "--tasks-file",
    type=Path,
    default=Path(os.environ.get("OSWORLD_TASKS_FILE", "config/stratified_tasks.json")),
    help="Pre-registered stratified task list used by --phase.",
  )
  parser.add_argument(
    "--failed-only",
    action="store_true",
    default=os.environ.get("OSWORLD_FAILED_ONLY", "") not in ("", "0", "false", "False"),
    help="Attribute only failed episodes; successful episodes are inventoried but not labeled.",
  )
  parser.add_argument("--taxonomy", type=Path, default=Path("failureTaxonomy.md"))
  parser.add_argument("--analysis-plan", type=Path, default=Path("failureAnalysisFinalPlan.md"))
  parser.add_argument(
    "--download-mode",
    choices=("auto", "never", "force"),
    default="auto",
    help="auto: use local/shared zip if present, otherwise hf download; never: fail if absent",
  )
  parser.add_argument("--judge-base-url", default=os.environ.get("JUDGE_BASE_URL", ""))
  parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", ""))
  parser.add_argument(
    "--judge-api-key",
    default=os.environ.get("ANTHROPIC_API_KEY", os.environ.get("JUDGE_API_KEY", "EMPTY")),
  )
  parser.add_argument(
    "--judge-provider",
    choices=("anthropic", "openai"),
    default=os.environ.get("JUDGE_PROVIDER", "anthropic"),
  )
  parser.add_argument(
    "--judge-max-calls",
    type=int,
    default=int(os.environ.get("JUDGE_MAX_CALLS", "50")),
  )
  return parser.parse_args()


def write_json(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def load_phase_task_ids(phase: str, tasks_file: Path) -> set[str] | None:
  """Return the pre-registered task IDs for ``phase`` (None means no filter)."""
  if phase == "all":
    return None
  if not tasks_file.exists():
    raise FileNotFoundError(
      f"--phase {phase} requires {tasks_file}; run scripts/build_stratified_tasks.py first."
    )
  data = json.loads(tasks_file.read_text(encoding="utf-8"))
  if phase == "pilot":
    ids = data.get("pilot_task_ids") or [t["task_id"] for t in data.get("tasks", [])[:30]]
  else:  # core
    ids = [t["task_id"] for t in data.get("tasks", [])]
  return set(ids)


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a", encoding="utf-8") as f:
    for row in rows:
      f.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_short(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()[:16]


def find_existing_package(args: argparse.Namespace) -> Path | None:
  candidates = [
    args.raw_root / args.package,
    args.shared_datasets_root / args.repo_id / args.package,
    args.shared_datasets_root / "xlangai" / "ubuntu_osworld_verified_trajs" / args.package,
    args.shared_datasets_root / "ubuntu_osworld_verified_trajs" / args.package,
  ]
  for candidate in candidates:
    if candidate.exists():
      return candidate

  try:
    matches = list(args.shared_datasets_root.glob(f"**/{args.package}"))
  except OSError:
    matches = []
  return matches[0] if matches else None


def ensure_package(args: argparse.Namespace) -> Path:
  args.raw_root.mkdir(parents=True, exist_ok=True)
  existing = None if args.download_mode == "force" else find_existing_package(args)
  if existing:
    return existing
  if args.download_mode == "never":
    raise FileNotFoundError(f"{args.package} not found and --download-mode=never")

  cmd = [
    "hf",
    "download",
    args.repo_id,
    "--repo-type",
    "dataset",
    "--revision",
    args.revision,
    "--include",
    args.package,
    "--local-dir",
    str(args.raw_root),
  ]
  try:
    subprocess.run(cmd, check=True)
  except (FileNotFoundError, subprocess.CalledProcessError):
    from huggingface_hub import hf_hub_download

    hf_hub_download(
      repo_id=args.repo_id,
      filename=args.package,
      repo_type="dataset",
      revision=args.revision,
      local_dir=args.raw_root,
    )

  downloaded = args.raw_root / args.package
  if not downloaded.exists():
    matches = list(args.raw_root.glob(f"**/{args.package}"))
    if matches:
      downloaded = matches[0]
  if not downloaded.exists():
    raise FileNotFoundError(f"Download completed but {args.package} was not found in {args.raw_root}")
  return downloaded


def top_dir(member: str) -> str:
  parts = [p for p in member.split("/") if p]
  if not parts:
    return "__root__"
  if re.match(r"^(task|example|episode|run|result)[-_]?\w*", parts[0], re.I):
    if len(parts) >= 2 and re.match(r"^(seed[-_]?)?\d+$", parts[1], re.I):
      return "/".join(parts[:2])
    return parts[0]
  if len(parts) >= 2 and re.match(r"^(task|example|episode|run|result)[-_]?\w*", parts[1], re.I):
    return "/".join(parts[:2])
  return parts[0]


def group_episodes(zf: zipfile.ZipFile) -> list[EpisodeCandidate]:
  groups: dict[str, list[str]] = defaultdict(list)
  for info in zf.infolist():
    if info.is_dir():
      continue
    groups[top_dir(info.filename)].append(info.filename)

  candidates: list[EpisodeCandidate] = []
  for episode_id, members in groups.items():
    json_members = [m for m in members if m.lower().endswith((".json", ".jsonl"))]
    text_members = [m for m in members if m.lower().endswith((".txt", ".md", ".log"))]
    image_members = [m for m in members if m.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    result_members = [
      m
      for m in json_members + text_members
      if re.search(r"(result|eval|score|traj|trace|step|history|log)", Path(m).name, re.I)
    ]
    if json_members or text_members or image_members:
      candidates.append(
        EpisodeCandidate(
          episode_id=episode_id,
          members=members,
          json_members=json_members,
          text_members=text_members,
          image_members=image_members,
          result_members=result_members,
        )
      )
  return sorted(candidates, key=lambda c: c.episode_id)


def safe_extract_members(zf: zipfile.ZipFile, members: list[str], dest: Path) -> list[Path]:
  extracted: list[Path] = []
  dest = dest.resolve()
  for member in members:
    target = (dest / member).resolve()
    if not str(target).startswith(str(dest)):
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, target.open("wb") as out:
      shutil.copyfileobj(src, out)
    extracted.append(target)
  return extracted


def read_jsonish(path: Path) -> Any | None:
  try:
    text = path.read_text(encoding="utf-8", errors="replace")
  except OSError:
    return None
  stripped = text.strip()
  if not stripped:
    return None
  if path.suffix.lower() == ".jsonl":
    rows = []
    for line in stripped.splitlines():
      line = line.strip()
      if not line:
        continue
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        return {"_raw_text": text[:4000], "_parse_error": "jsonl_decode"}
    return rows
  try:
    return json.loads(stripped)
  except json.JSONDecodeError:
    return {"_raw_text": text[:4000], "_parse_error": "json_decode"}


def flatten_records(obj: Any) -> list[dict[str, Any]]:
  if isinstance(obj, list):
    out = []
    for item in obj:
      out.extend(flatten_records(item))
    return out
  if not isinstance(obj, dict):
    return []

  records: list[dict[str, Any]] = []
  if any(k in obj for k in REASONING_KEYS + ACTION_KEYS + SUCCESS_KEYS) or "step" in obj:
    records.append(obj)
  for key in ("trajectory", "steps", "history", "messages", "actions", "logs", "records"):
    child = obj.get(key)
    if isinstance(child, list):
      for item in child:
        records.extend(flatten_records(item))
  return records


def first_string(record: dict[str, Any], keys: tuple[str, ...]) -> str:
  for key in keys:
    value = record.get(key)
    if isinstance(value, str) and value.strip():
      return value.strip()
    if isinstance(value, dict):
      nested = first_string(value, keys)
      if nested:
        return nested
  return ""


def first_action(record: dict[str, Any]) -> Any:
  for key in ACTION_KEYS:
    if key in record and record[key]:
      return record[key]
  return {}


def infer_success(records: list[dict[str, Any]], parsed_files: list[tuple[Path, Any]]) -> bool | None:
  for record in records:
    for key in SUCCESS_KEYS:
      if key not in record:
        continue
      value = record[key]
      if isinstance(value, bool):
        return value
      if isinstance(value, (int, float)) and key == "score":
        return value > 0
      if isinstance(value, str):
        lower = value.lower()
        if lower in {"success", "passed", "pass", "true"}:
          return True
        if lower in {"failure", "failed", "fail", "false"}:
          return False
  for _, data in parsed_files:
    text = json.dumps(data, default=str).lower()[:20000]
    if re.search(r'"success"\s*:\s*true|"passed"\s*:\s*true', text):
      return True
    if re.search(r'"success"\s*:\s*false|"passed"\s*:\s*false', text):
      return False
  return None


def normalize_episode(
  package: str,
  model_id: str,
  candidate: EpisodeCandidate,
  extracted_paths: list[Path],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
  parsed_files: list[tuple[Path, Any]] = []
  records: list[dict[str, Any]] = []
  for path in extracted_paths:
    if path.suffix.lower() not in {".json", ".jsonl"}:
      continue
    parsed = read_jsonish(path)
    if parsed is None:
      continue
    parsed_files.append((path, parsed))
    records.extend(flatten_records(parsed))

  success = infer_success(records, parsed_files)
  trace_steps: list[dict[str, Any]] = []
  for idx, record in enumerate(records):
    reasoning = first_string(record, REASONING_KEYS)
    action = first_action(record)
    if not reasoning and not action:
      continue
    step_value = record.get("step", record.get("step_id", record.get("index", idx)))
    try:
      step = int(step_value)
    except (TypeError, ValueError):
      step = idx
    trace_steps.append(
      {
        "task_id": candidate.episode_id,
        "seed": 0,
        "step": step,
        "screenshot_path": "",
        "action": action if isinstance(action, dict) else {"raw": action},
        "coords": record.get("coords") or record.get("coordinate") or record.get("position"),
        "cot": reasoning,
        "eval_signals": {"raw_success": success},
        "a11y_snippet": [],
        "task_tags": [],
        "instruction": first_string(record, ("instruction", "task", "goal", "query")),
        "eval_passed": success if idx == len(records) - 1 else None,
        "state_hash": None,
      }
    )

  manifest = {
    "package": package,
    "model_id": model_id,
    "episode_id": candidate.episode_id,
    "success": success,
    "num_members": len(candidate.members),
    "num_json_members": len(candidate.json_members),
    "num_text_members": len(candidate.text_members),
    "num_image_members": len(candidate.image_members),
    "num_result_members": len(candidate.result_members),
    "num_records": len(records),
    "num_normalized_steps": len(trace_steps),
    "result_members": candidate.result_members[:20],
  }
  return manifest, trace_steps


def infer_model_id(package: str) -> str:
  name = package
  name = name.removesuffix(".zip")
  name = re.sub(r"_?Ubuntu.*$", "", name)
  name = name.replace("opencua_agent-", "")
  name = name.replace("_", "-")
  return name


def classify_best_effort(manifest: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
  """Cheap placeholder classifier until package-specific adapters are calibrated.

  This intentionally avoids overclaiming. It identifies obvious looping and
  otherwise queues the case for judge/human review with reasoning evidence.
  """
  if not steps:
    return {
      "primary_mode": "Unresolved",
      "secondary_modes": [],
      "confidence": 0.0,
      "t_star": 0,
      "needs_human_review": True,
      "evidence": "No normalized reasoning/action steps found; adapter needs package-specific mapping.",
      "adapter_status": "needs_mapping",
    }

  t_star = steps[-1]["step"]
  actions = [json.dumps(s.get("action", {}), sort_keys=True, default=str) for s in steps[-3:]]
  if len(actions) == 3 and len(set(actions)) == 1:
    return {
      "primary_mode": "Action Looping (Repetition)",
      "secondary_modes": [],
      "confidence": 0.65,
      "t_star": t_star,
      "needs_human_review": True,
      "evidence": "Last three normalized actions are identical; verify root cause and propagation manually.",
      "adapter_status": "best_effort",
    }

  last = steps[-1]
  return {
    "primary_mode": "Unresolved",
    "secondary_modes": [],
    "confidence": 0.0,
    "t_star": t_star,
    "needs_human_review": True,
    "evidence": (last.get("cot") or "")[:500],
    "adapter_status": "best_effort",
  }


def _inventory_row(
  episode_id: str,
  members: list[str],
  json_members: list[str],
  text_members: list[str],
  image_members: list[str],
  result_members: list[str],
) -> dict[str, Any]:
  return {
    "episode_id": episode_id,
    "num_members": len(members),
    "num_json_members": len(json_members),
    "num_text_members": len(text_members),
    "num_image_members": len(image_members),
    "num_result_members": len(result_members),
    "sample_members": members[:20],
    "result_members": result_members[:20],
  }


def _opencua_members_to_extract(bundle: EpisodeBundle) -> list[str]:
  names = ("traj.jsonl", "result.txt", "instruction.txt")
  members: list[str] = []
  for name in names:
    member = f"{bundle.episode_id}/{name}"
    if member in bundle.members:
      members.append(member)
  return members


def _write_normalized_trace(
  output_dir: Path,
  episode_id: str,
  steps: list[TraceStep],
  manifest: RunManifest,
) -> Path:
  trace_dir = output_dir / "normalized_traces" / episode_id
  trace_dir.mkdir(parents=True, exist_ok=True)
  trace_path = trace_dir / "trace.jsonl"
  with trace_path.open("w", encoding="utf-8") as f:
    for step in steps:
      f.write(step.model_dump_json() + "\n")
  (trace_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
  return trace_path


def _build_judge(args: argparse.Namespace) -> JudgeClient | None:
  provider = args.judge_provider
  api_key = (args.judge_api_key or "").strip()
  if api_key in {"", "EMPTY"}:
    if provider == "openai" and args.judge_base_url:
      model = args.judge_model or "opencua-7b"
      return VLMJudge(VLMJudgeConfig(base_url=args.judge_base_url, api_key=api_key, model=model))
    return None

  if provider == "anthropic":
    model = args.judge_model or "claude-sonnet-4-6"
    return AnthropicJudge(AnthropicJudgeConfig(api_key=api_key, model=model))

  if args.judge_base_url:
    model = args.judge_model or "opencua-7b"
    return VLMJudge(
      VLMJudgeConfig(
        base_url=args.judge_base_url,
        api_key=api_key,
        model=model,
      )
    )
  return None


def _prepare_trace_for_judge(
  trace_path: Path,
  zf: zipfile.ZipFile,
  bundle: EpisodeBundle,
  work_dir: Path,
) -> None:
  steps = load_trace(trace_path)
  if not steps:
    return
  t_idx = find_first_failure_step(steps)
  step = steps[t_idx]
  local_path = extract_screenshot_for_judge(zf, bundle, step, work_dir)
  if local_path is None:
    return
  steps[t_idx] = step.model_copy(update={"screenshot_path": str(local_path)})
  with trace_path.open("w", encoding="utf-8") as f:
    for row in steps:
      f.write(row.model_dump_json() + "\n")


def _label_from_attribution(
  trace_path: Path,
  instruction: str,
  *,
  judge: JudgeClient | None = None,
  zf: zipfile.ZipFile | None = None,
  bundle: EpisodeBundle | None = None,
  work_dir: Path | None = None,
  judge_calls_remaining: list[int] | None = None,
  judge_usage_path: Path | None = None,
  episode_id: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
  active_judge = judge
  if active_judge is not None and zf is not None and bundle is not None and work_dir is not None:
    if judge_calls_remaining is not None and judge_calls_remaining[0] <= 0:
      active_judge = None
    elif judge is not None:
      _prepare_trace_for_judge(trace_path, zf, bundle, work_dir)

  result = attribute_run(trace_path, instruction=instruction, judge=active_judge)

  usage_row: dict[str, Any] | None = None
  if result.tier_used == "judge" and isinstance(active_judge, AnthropicJudge):
    if active_judge.last_usage and judge_usage_path is not None:
      usage_row = log_judge_usage(
        judge_usage_path,
        episode_id=episode_id,
        model=active_judge.last_usage.model,
        usage=active_judge.last_usage,
        primary_mode=result.primary_mode,
      )
    if judge_calls_remaining is not None:
      judge_calls_remaining[0] -= 1

  label = {
    "status": "failed",
    "primary_mode": result.primary_mode,
    "secondary_modes": result.secondary_modes,
    "propagated": result.propagated,
    "meta_labels": result.meta_labels,
    "confidence": result.confidence,
    "t_star": result.t_star,
    "tier_used": result.tier_used,
    "needs_human_review": True,
    "evidence": result.evidence_cot_span,
    "adapter_status": "mapped",
  }
  return label, usage_row


def _label_success_episode() -> dict[str, Any]:
  return {
    "status": "success",
    "primary_mode": None,
    "secondary_modes": [],
    "confidence": 1.0,
    "t_star": None,
    "tier_used": "n/a",
    "needs_human_review": False,
    "evidence": "",
    "adapter_status": "mapped",
  }


def _adapter_manifest_dict(
  package: str,
  model_id: str,
  bundle: EpisodeBundle,
  manifest: RunManifest,
  num_steps: int,
) -> dict[str, Any]:
  return {
    "package": package,
    "model_id": model_id,
    "episode_id": bundle.episode_id,
    "task_id": bundle.task_id,
    "domain": bundle.domain,
    "success": manifest.success,
    "instruction": manifest.instruction,
    "num_members": len(bundle.members),
    "num_json_members": len(bundle.json_members),
    "num_text_members": len(bundle.text_members),
    "num_image_members": len(bundle.image_members),
    "num_result_members": len(bundle.result_members),
    "num_normalized_steps": num_steps,
    "result_members": bundle.result_members[:20],
  }


def write_summary(
  output_dir: Path,
  package_path: Path,
  package: str,
  model_id: str,
  episodes_inventoried: int,
  labels: list[dict[str, Any]],
  adapter_gaps: list[dict[str, Any]],
  judge_usage_rows: list[dict[str, Any]] | None = None,
) -> None:
  counts = Counter(row["primary_mode"] for row in labels if row.get("primary_mode"))
  review_count = sum(1 for row in labels if row.get("needs_human_review"))
  judge_summary = summarize_judge_usage(judge_usage_rows or [])
  lines = [
    f"# HF OSWorld Failure Analysis: {model_id}",
    "",
    f"- Package: `{package}`",
    f"- Zip path: `{package_path}`",
    f"- Episodes inventoried: {episodes_inventoried}",
    f"- Episodes analyzed/sample-labeled: {len(labels)}",
    f"- Human review queue: {review_count}",
    f"- Adapter gaps: {len(adapter_gaps)}",
    "",
    "## Primary Label Counts",
    "",
  ]
  if counts:
    for label, count in counts.most_common():
      lines.append(f"- {label}: {count}")
  else:
    lines.append("- No labels emitted.")

  if judge_summary["judge_calls"]:
    lines.extend(
      [
        "",
        "## Judge Usage (provisional cost estimate)",
        "",
        f"- Judge calls: {judge_summary['judge_calls']}",
        f"- Input tokens: {judge_summary['input_tokens']}",
        f"- Output tokens: {judge_summary['output_tokens']}",
        f"- Estimated USD: ${judge_summary['estimated_cost_usd']:.4f}",
      ]
    )

  lines.extend(
    [
      "",
      "## Interpretation Guardrail",
      "",
      "This run uses Tier-1 detectors plus an optional frontier judge on unresolved "
      "failed episodes. Treat all labels and `needs_human_review=true` as provisional "
      "until human gold-set calibration.",
      "",
      "## Next Actions",
      "",
      "1. Inspect `zip_inventory.json` and `adapter_gaps.json`.",
      "2. Confirm which files contain step-level reasoning/action traces.",
      "3. Add or tune the package-specific mapping.",
      "4. Rerun on 20-50 failed episodes with a calibrated judge.",
    ]
  )
  (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
  args = parse_args()
  args.output_dir.mkdir(parents=True, exist_ok=True)
  args.work_root.mkdir(parents=True, exist_ok=True)

  package_path = ensure_package(args)
  model_id = infer_model_id(args.package)
  judge = _build_judge(args)
  judge_usage_path = args.output_dir / "judge_usage.jsonl"
  judge_usage_rows: list[dict[str, Any]] = []
  judge_calls_remaining = [args.judge_max_calls] if judge is not None else None

  run_meta = {
    "repo_id": args.repo_id,
    "revision": args.revision,
    "package": args.package,
    "package_path": str(package_path),
    "package_sha256_short": sha256_short(package_path),
    "model_id": model_id,
    "taxonomy": str(args.taxonomy),
    "analysis_plan": str(args.analysis_plan),
    "max_episodes": args.max_episodes,
    "hf_home": os.environ.get("HF_HOME", ""),
    "judge_provider": args.judge_provider if judge is not None else None,
    "judge_model": args.judge_model or (
      judge.config.model if isinstance(judge, AnthropicJudge) else ""
    ),
    "judge_max_calls": args.judge_max_calls if judge is not None else 0,
  }
  write_json(args.output_dir / "run_metadata.json", run_meta)

  labels: list[dict[str, Any]] = []
  manifests: list[dict[str, Any]] = []
  adapter_gaps: list[dict[str, Any]] = []
  episodes_inventoried = 0

  phase_task_ids = load_phase_task_ids(args.phase, args.tasks_file)

  with zipfile.ZipFile(package_path) as zf:
    adapter = get_adapter(args.package)
    if uses_opencua_grouping(args.package):
      bundles = group_opencua_episodes(zf)
      episodes_inventoried = len(bundles)
      inventory = [
        _inventory_row(
          b.episode_id,
          b.members,
          b.json_members,
          b.text_members,
          b.image_members,
          b.result_members,
        )
        for b in bundles
      ]
      write_json(args.output_dir / "zip_inventory.json", inventory)

      if phase_task_ids is not None:
        present = {b.task_id for b in bundles}
        write_json(
          args.output_dir / "phase_task_coverage.json",
          {
            "phase": args.phase,
            "expected": sorted(phase_task_ids),
            "present": sorted(phase_task_ids & present),
            "missing": sorted(phase_task_ids - present),
            "n_expected": len(phase_task_ids),
            "n_present": len(phase_task_ids & present),
          },
        )
        bundles = [b for b in bundles if b.task_id in phase_task_ids]

      for bundle in bundles[: args.max_episodes]:
        with tempfile.TemporaryDirectory(dir=args.work_root) as tmp:
          tmp_path = Path(tmp)
          members_to_extract = _opencua_members_to_extract(bundle)
          extracted = safe_extract_members(zf, members_to_extract, tmp_path)
          try:
            result = adapter.normalize_episode(
              bundle,
              extracted,
              model_id=model_id,
              package=args.package,
            )
          except ValueError as exc:
            manifests.append(
              {
                "package": args.package,
                "model_id": model_id,
                "episode_id": bundle.episode_id,
                "num_normalized_steps": 0,
                "error": str(exc),
              }
            )
            adapter_gaps.append(
              {
                "episode_id": bundle.episode_id,
                "reason": str(exc),
                "result_members": bundle.result_members[:20],
                "json_members": bundle.json_members[:20],
                "text_members": bundle.text_members[:20],
              }
            )
            continue

          manifests.append(
            _adapter_manifest_dict(
              args.package,
              model_id,
              bundle,
              result.manifest,
              len(result.steps),
            )
          )

          if not result.steps:
            adapter_gaps.append(
              {
                "episode_id": bundle.episode_id,
                "reason": "No normalized reasoning/action steps found",
                "result_members": bundle.result_members[:20],
                "json_members": bundle.json_members[:20],
                "text_members": bundle.text_members[:20],
              }
            )
            continue

          trace_path = _write_normalized_trace(
            args.output_dir,
            bundle.episode_id,
            result.steps,
            result.manifest,
          )

          if result.manifest.success:
            if args.failed_only:
              continue
            label = _label_success_episode()
            usage_row = None
          else:
            label, usage_row = _label_from_attribution(
              trace_path,
              result.manifest.instruction,
              judge=judge,
              zf=zf,
              bundle=bundle,
              work_dir=tmp_path,
              judge_calls_remaining=judge_calls_remaining,
              judge_usage_path=judge_usage_path,
              episode_id=bundle.episode_id,
            )
          if usage_row:
            judge_usage_rows.append(usage_row)

          labels.append(
            {
              "model_id": model_id,
              "package": args.package,
              "episode_id": bundle.episode_id,
              "success": result.manifest.success,
              **label,
            }
          )
    else:
      candidates = group_episodes(zf)
      episodes_inventoried = len(candidates)
      inventory = [
        _inventory_row(
          c.episode_id,
          c.members,
          c.json_members,
          c.text_members,
          c.image_members,
          c.result_members,
        )
        for c in candidates
      ]
      write_json(args.output_dir / "zip_inventory.json", inventory)

      for candidate in candidates[: args.max_episodes]:
        with tempfile.TemporaryDirectory(dir=args.work_root) as tmp:
          tmp_path = Path(tmp)
          members_to_extract = candidate.json_members + candidate.text_members[:10]
          extracted = safe_extract_members(zf, members_to_extract, tmp_path)
          manifest, steps = normalize_episode(args.package, model_id, candidate, extracted)
          manifests.append(manifest)

          label = classify_best_effort(manifest, steps)
          labels.append(
            {
              "model_id": model_id,
              "package": args.package,
              "episode_id": candidate.episode_id,
              "success": manifest["success"],
              **label,
            }
          )

          if label["adapter_status"] == "needs_mapping" or manifest["num_normalized_steps"] == 0:
            adapter_gaps.append(
              {
                "episode_id": candidate.episode_id,
                "reason": "No normalized reasoning/action steps found",
                "result_members": candidate.result_members[:20],
                "json_members": candidate.json_members[:20],
                "text_members": candidate.text_members[:20],
              }
            )

  write_json(args.output_dir / "episode_manifests.json", manifests)
  write_json(args.output_dir / "adapter_gaps.json", adapter_gaps)
  append_jsonl(args.output_dir / "failure_labels.jsonl", labels)
  append_jsonl(args.output_dir / "human_review_queue.jsonl", [r for r in labels if r.get("needs_human_review")])

  with (args.output_dir / "aggregate_stats.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["primary_mode", "count"])
    writer.writeheader()
    for primary_mode, count in Counter(
      r["primary_mode"] for r in labels if r.get("primary_mode")
    ).most_common():
      writer.writerow({"primary_mode": primary_mode, "count": count})

  write_summary(
    args.output_dir,
    package_path,
    args.package,
    model_id,
    episodes_inventoried,
    labels,
    adapter_gaps,
    judge_usage_rows=judge_usage_rows,
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
