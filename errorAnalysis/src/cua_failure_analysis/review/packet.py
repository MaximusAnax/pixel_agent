"""Build static HTML trace review packets from HF trajectory zips."""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cua_failure_analysis.adapters.grouping import group_opencua_episodes
from cua_failure_analysis.adapters.opencua_osworld import (
  ACTION_SECTION_RE,
  THOUGHT_RE,
  _parse_result_txt,
  _step_number,
)
from cua_failure_analysis.attribution.pipeline import (
  load_human_reference_steps,
  resolve_oracle_dir,
)
from cua_failure_analysis.osworld.eval_bundle import format_eval_bundle
from cua_failure_analysis.osworld.grounding import compare_proposed_vs_executed
from cua_failure_analysis.osworld.human_ref import load_human_reference
from cua_failure_analysis.osworld.metadata import load_sources, task_lookup
from cua_failure_analysis.review.labels import judge_modes_ordered, label_storage_key
from cua_failure_analysis.taxonomy import ALL_LEAVES

STEP_SCREENSHOT_RE = re.compile(r"^step_(\d+)_", re.I)
CODE_BLOCK_RE = re.compile(r"```(?:python|code)\s*(.*?)```", re.S | re.I)


@dataclass
class ParsedStep:
  step_num: int
  action: str
  thought: str
  action_section: str
  code: str
  model_code: str
  stated_intent: str
  screenshot_file: str | None
  reward: Any
  done: bool
  grounding_mismatch: bool = False
  grounding_note: str = ""


def episode_slug(episode_id: str) -> str:
  return episode_id.replace("/", "__")


def parse_traj_steps(traj_path: Path) -> list[ParsedStep]:
  steps: list[ParsedStep] = []
  for idx, line in enumerate(traj_path.read_text(encoding="utf-8", errors="replace").splitlines()):
    line = line.strip()
    if not line:
      continue
    record = json.loads(line)
    response = str(record.get("response") or "")
    action_raw = str(record.get("action") or "").strip()
    step_num = _step_number(record, response, idx + 1)
    thought_match = THOUGHT_RE.search(response)
    action_match = ACTION_SECTION_RE.search(response)
    code_match = CODE_BLOCK_RE.search(response)
    model_code = code_match.group(1).strip() if code_match else ""
    stated_intent = action_match.group(1).strip()[:500] if action_match else ""
    comparison = compare_proposed_vs_executed(model_code, action_raw)
    note = ""
    if comparison.get("coords_model_pixels_est") and comparison.get("coords_executed"):
      mx, my = comparison["coords_model_pixels_est"]
      ex, ey = comparison["coords_executed"]
      note = f"≈ ({mx:.0f}, {my:.0f}) est. vs executed ({ex:.0f}, {ey:.0f})"
      if comparison.get("grounding_mismatch"):
        note += " → mismatch"
    steps.append(
      ParsedStep(
        step_num=step_num,
        action=action_raw,
        thought=thought_match.group(1).strip() if thought_match else response[:2000],
        action_section=stated_intent,
        code=model_code,
        model_code=model_code,
        stated_intent=stated_intent,
        screenshot_file=str(record.get("screenshot_file") or "") or None,
        reward=record.get("reward"),
        done=bool(record.get("done")),
        grounding_mismatch=bool(comparison.get("grounding_mismatch")),
        grounding_note=note,
      )
    )
  return steps


def _members_for_review(bundle_members: list[str]) -> list[str]:
  names = {"traj.jsonl", "result.txt", "instruction.txt", "runtime.log"}
  picked: list[str] = []
  for member in bundle_members:
    base = Path(member).name
    if base in names or STEP_SCREENSHOT_RE.match(base):
      picked.append(member)
  return sorted(picked)


def _extract_members(zf: zipfile.ZipFile, members: list[str], dest: Path) -> dict[str, Path]:
  dest = dest.resolve()
  out: dict[str, Path] = {}
  for member in members:
    target = (dest / Path(member).name).resolve()
    if not str(target).startswith(str(dest)):
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, target.open("wb") as fh:
      shutil.copyfileobj(src, fh)
    out[member] = target
  return out


def _load_instruction(stratified_path: Path | None, task_id: str) -> str:
  if stratified_path is None or not stratified_path.exists():
    return ""
  data = json.loads(stratified_path.read_text(encoding="utf-8"))
  for row in data.get("tasks", []):
    if row.get("task_id") == task_id:
      return str(row.get("instruction") or row.get("prompt") or "")
  return ""


def _render_template(template_dir: Path, name: str, **ctx: Any) -> str:
  try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
  except ImportError as exc:
    raise ImportError("jinja2 is required for trace review packets; pip install jinja2") from exc

  env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=select_autoescape(["html", "xml"]),
  )
  return env.get_template(name).render(**ctx)


def _copy_static_assets(template_dir: Path, output_dir: Path) -> None:
  for name in ("review.js", "review.css"):
    src = template_dir / name
    if src.exists():
      shutil.copy2(src, output_dir / name)


def _empty_annotations(packet_id: str) -> dict[str, Any]:
  from cua_failure_analysis.review.annotations import empty_annotations

  return empty_annotations(packet_id)


def _osworld_episode_context(
  task_id: str,
  domain: str,
  *,
  success: bool | None,
  result_raw: str,
) -> dict[str, Any]:
  """Best-effort eval bundle + text human refs from vendored OSWorld pin."""
  out: dict[str, Any] = {
    "eval_bundle": "",
    "canonical_instruction": "",
    "human_reference_actions": [],
  }
  try:
    sources = load_sources()
    task = task_lookup(task_id, domain=domain or None, sources=sources)
  except (FileNotFoundError, OSError, ValueError, KeyError):
    return out

  out["canonical_instruction"] = str(task.get("instruction") or "")
  domain_resolved = str(task.get("_domain") or domain or "")
  try:
    result_val: Any
    if result_raw.strip() == "":
      result_val = None
    else:
      try:
        result_val = float(result_raw)
      except ValueError:
        result_val = result_raw
    out["eval_bundle"] = format_eval_bundle(
      task,
      result_txt=result_val if success is not None or result_raw else None,
      pin_dir=sources.pin_dir,
    )
  except (FileNotFoundError, OSError, ValueError, TypeError, KeyError):
    pass

  try:
    ref = load_human_reference(
      task_id, domain=domain_resolved or None, sources=sources
    )
    out["human_reference_actions"] = list(ref.single_action)
  except (FileNotFoundError, OSError, ValueError, KeyError):
    pass
  return out


def _stage_human_assets(
  episode_dir: Path,
  *,
  domain: str,
  task_id: str,
  oracle_root: Path | None,
  text_actions: list[str],
) -> dict[str, Any]:
  """Copy partner screenshots into episode_dir/human/ when available."""
  oracle_dir = resolve_oracle_dir(oracle_root, domain, task_id)
  steps, status = load_human_reference_steps(oracle_dir=oracle_dir)

  human_dir = episode_dir / "human"
  staged: list[dict[str, Any]] = []
  if steps:
    human_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(steps, start=1):
      action_text = str(row.get("action_text") or "")
      rel_shot = ""
      src = row.get("image_path")
      if src:
        src_path = Path(str(src))
        if src_path.exists():
          dest_name = src_path.name or f"human_step_{i}_obs.png"
          dest = human_dir / dest_name
          if src_path.resolve() != dest.resolve():
            shutil.copy2(src_path, dest)
          rel_shot = f"human/{dest_name}"
      staged.append(
        {
          "step": i,
          "action_text": action_text,
          "screenshot": rel_shot,
        }
      )
  elif text_actions:
    status = status if status not in {"", "pending"} else "pending"
    for i, action_text in enumerate(text_actions, start=1):
      staged.append({"step": i, "action_text": str(action_text), "screenshot": ""})

  return {
    "oracle_status": status or "pending",
    "human_steps": staged,
    "oracle_dir": str(oracle_dir) if oracle_dir else "",
  }


def _step_rows(assets: dict[str, Any], t_star: Any) -> list[dict[str, Any]]:
  rows = []
  for step in assets["steps"]:
    shot = assets["screenshot_by_step"].get(step.step_num)
    rows.append(
      {
        "step_num": step.step_num,
        "action": step.action,
        "thought": step.thought,
        "action_section": step.action_section,
        "code": step.code,
        "model_code": step.model_code,
        "stated_intent": step.stated_intent,
        "reward": step.reward,
        "done": step.done,
        "screenshot": shot,
        "is_t_star": t_star is not None and step.step_num == int(t_star),
        "grounding_mismatch": step.grounding_mismatch,
        "grounding_note": step.grounding_note,
      }
    )
  return rows


def _build_side_nav(episodes: list[dict[str, Any]], current_idx: int) -> list[dict[str, Any]]:
  """Deduped task list for left sidebar (prefer a3b href when both present)."""
  seen: dict[str, dict[str, Any]] = {}
  order: list[str] = []
  for ep in episodes:
    task_id = str(ep.get("task_id") or "")
    if not task_id:
      continue
    if task_id not in seen:
      order.append(task_id)
      slug = episode_slug(ep["episode_id"])
      href = f"../../{ep['model']}/{slug}/episode.html"
      seen[task_id] = {
        "domain": ep.get("domain", ""),
        "task_id": task_id,
        "task_short": task_id[:8],
        "instruction_preview": (ep.get("instruction") or "")[:120],
        "href": href,
        "active": False,
      }
    elif ep.get("model") == "a3b":
      slug = episode_slug(ep["episode_id"])
      seen[task_id]["href"] = f"../../{ep['model']}/{slug}/episode.html"
  current_task = ""
  if 0 <= current_idx < len(episodes):
    current_task = str(episodes[current_idx].get("task_id") or "")
  out = []
  for tid in order:
    row = dict(seen[tid])
    row["active"] = tid == current_task
    out.append(row)
  return out


def _episode_render_ctx(
  *,
  manifest: dict[str, Any],
  ep: dict[str, Any],
  assets: dict[str, Any],
  idx: int,
  episodes: list[dict[str, Any]],
  taxonomy_leaves: list[str],
  stratified_tasks: Path | None,
  oracle_root: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
  model = ep["model"]
  episode_id = ep["episode_id"]
  task_id = ep.get("task_id") or episode_id.split("/", 1)[-1]
  domain = str(ep.get("domain") or "")
  osw = _osworld_episode_context(
    task_id,
    domain,
    success=assets["success"],
    result_raw=assets["result_raw"],
  )
  instruction = (
    ep.get("instruction")
    or osw.get("canonical_instruction")
    or _load_instruction(stratified_tasks, task_id)
  )
  human_pack = _stage_human_assets(
    assets["episode_dir"],
    domain=domain,
    task_id=task_id,
    oracle_root=oracle_root,
    text_actions=list(osw.get("human_reference_actions") or []),
  )
  has_mismatch = any(s.grounding_mismatch for s in assets["steps"])
  judge_modes = judge_modes_ordered(ep)
  sibling_href = ep.get("sibling_href") or ""
  sibling_model = "7b" if model == "a3b" else "a3b" if sibling_href else ""
  label_key = label_storage_key(model, episode_id)
  t_star = ep.get("t_star")

  prev_link = next_link = None
  if idx > 0:
    prev_slug = episode_slug(episodes[idx - 1]["episode_id"])
    prev_link = f"../../{episodes[idx - 1]['model']}/{prev_slug}/episode.html"
  if idx + 1 < len(episodes):
    next_slug = episode_slug(episodes[idx + 1]["episode_id"])
    next_link = f"../../{episodes[idx + 1]['model']}/{next_slug}/episode.html"

  side_nav = _build_side_nav(
    [
      {
        **e,
        "instruction": e.get("instruction")
        or (
          osw.get("canonical_instruction")
          if e.get("task_id") == task_id
          else e.get("instruction", "")
        ),
      }
      for e in episodes
    ],
    idx,
  )
  # Enrich side_nav previews lazily only for known tasks would be heavy; keep short IDs.

  ctx = {
    "packet_id": manifest.get("packet_id", ""),
    "model": model,
    "episode_id": episode_id,
    "domain": domain,
    "task_id": task_id,
    "instruction": instruction,
    "success": assets["success"],
    "result_raw": assets["result_raw"],
    "eval_bundle": osw.get("eval_bundle") or ep.get("eval_bundle") or "",
    "oracle_status": human_pack["oracle_status"],
    "human_steps": human_pack["human_steps"],
    "has_action_mismatch": has_mismatch,
    "provisional_primary": ep.get("provisional_primary", ""),
    "judge_modes_ordered": judge_modes,
    "secondary_modes": ep.get("secondary_modes") or [],
    "propagated": ep.get("propagated", False),
    "t_star": t_star,
    "evidence": ep.get("evidence", ""),
    "confidence": ep.get("confidence"),
    "tier_used": ep.get("tier_used"),
    "judge_context_version": ep.get("judge_context_version") or "",
    "steps": _step_rows(assets, t_star),
    "prev_link": prev_link,
    "next_link": next_link,
    "index_href": "../../index.html",
    "sibling_href": sibling_href,
    "sibling_model": sibling_model,
    "label_key": label_key,
    "taxonomy_leaves": taxonomy_leaves,
    "side_nav": side_nav,
    "api_base": "",
    "default_annotator": "abdoul",
  }
  page_meta = {
    "model": model,
    "domain": domain,
    "task_id": task_id,
    "episode_id": episode_id,
    "provisional_primary": ep.get("provisional_primary", ""),
    "t_star": t_star,
    "confusing": ep.get("confusing", False),
    "oracle_status": human_pack["oracle_status"],
    "href": f"{model}/{episode_slug(episode_id)}/episode.html",
    "instruction": instruction,
  }
  return ctx, page_meta


def build_episode_assets(
  zf: zipfile.ZipFile,
  episode_id: str,
  bundle_members: list[str],
  episode_dir: Path,
  *,
  select_turn: str | None = None,
) -> dict[str, Any]:
  """Extract media + parse traj for one episode into ``episode_dir``."""
  members = _members_for_review(bundle_members)
  extracted = _extract_members(zf, members, episode_dir)

  traj_path = episode_dir / "traj.jsonl"
  if not traj_path.exists():
    raise FileNotFoundError(f"No traj.jsonl extracted for {episode_id}")

  result_path = episode_dir / "result.txt"
  success = _parse_result_txt(result_path)
  steps = parse_traj_steps(traj_path)

  screenshot_by_step: dict[int, str] = {}
  for member, path in extracted.items():
    match = STEP_SCREENSHOT_RE.match(Path(member).name)
    if match:
      screenshot_by_step[int(match.group(1))] = path.name

  for step in steps:
    if step.screenshot_file:
      screenshot_by_step.setdefault(step.step_num, Path(step.screenshot_file).name)

  return {
    "episode_id": episode_id,
    "episode_dir": episode_dir,
    "success": success,
    "result_raw": result_path.read_text(encoding="utf-8", errors="replace").strip()
    if result_path.exists()
    else "",
    "steps": steps,
    "screenshot_by_step": screenshot_by_step,
    "select_turn": select_turn,
  }


def _assets_from_episode_dir(episode_dir: Path, episode_id: str) -> dict[str, Any]:
  """Load traj + screenshots already on disk (no zip extraction)."""
  traj_path = episode_dir / "traj.jsonl"
  if not traj_path.exists():
    raise FileNotFoundError(f"No traj.jsonl in {episode_dir}")

  result_path = episode_dir / "result.txt"
  success = _parse_result_txt(result_path) if result_path.exists() else None
  steps = parse_traj_steps(traj_path)

  screenshot_by_step: dict[int, str] = {}
  for path in episode_dir.iterdir():
    if not path.is_file():
      continue
    match = STEP_SCREENSHOT_RE.match(path.name)
    if match:
      screenshot_by_step[int(match.group(1))] = path.name

  for step in steps:
    if step.screenshot_file:
      screenshot_by_step.setdefault(step.step_num, Path(step.screenshot_file).name)

  return {
    "episode_id": episode_id,
    "episode_dir": episode_dir,
    "success": success,
    "result_raw": result_path.read_text(encoding="utf-8", errors="replace").strip()
    if result_path.exists()
    else "",
    "steps": steps,
    "screenshot_by_step": screenshot_by_step,
    "select_turn": None,
  }


def _resolve_oracle_root(explicit: Path | None = None) -> Path | None:
  if explicit is not None:
    return explicit
  env = os.environ.get("ORACLE_ROOT", "").strip()
  return Path(env) if env else None


def refresh_review_packet_html(
  packet_dir: Path,
  *,
  template_dir: Path,
  stratified_tasks: Path | None = None,
  oracle_root: Path | None = None,
) -> Path:
  """Re-render index + episode HTML from on-disk assets (template updates, no zips)."""
  manifest_path = packet_dir / "packet_manifest.json"
  if not manifest_path.exists():
    manifest_path = packet_dir / "manifest.json"
  if not manifest_path.exists():
    raise FileNotFoundError(f"No manifest in {packet_dir}")

  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  episodes: list[dict[str, Any]] = manifest.get("episodes", [])
  taxonomy_leaves = sorted({leaf.value for leaf in ALL_LEAVES})
  _copy_static_assets(template_dir, packet_dir)
  oracle_root = _resolve_oracle_root(oracle_root)

  episode_pages: list[dict[str, Any]] = []
  for idx, ep in enumerate(episodes):
    model = ep["model"]
    episode_id = ep["episode_id"]
    slug = episode_slug(episode_id)
    episode_dir = packet_dir / model / slug
    assets = _assets_from_episode_dir(episode_dir, episode_id)
    ctx, page_meta = _episode_render_ctx(
      manifest=manifest,
      ep=ep,
      assets=assets,
      idx=idx,
      episodes=episodes,
      taxonomy_leaves=taxonomy_leaves,
      stratified_tasks=stratified_tasks,
      oracle_root=oracle_root,
    )
    (episode_dir / "episode.html").write_text(
      _render_template(template_dir, "episode.html.j2", **ctx),
      encoding="utf-8",
    )
    episode_pages.append(page_meta)

  task_groups = _enrich_task_groups(manifest.get("task_groups") or [], episode_pages)
  (packet_dir / "index.html").write_text(
    _render_template(
      template_dir,
      "index.html.j2",
      packet_id=manifest.get("packet_id", ""),
      episodes=episode_pages,
      task_groups=task_groups,
      side_nav=_index_side_nav(episode_pages),
      n_episodes=len(episode_pages),
      n_tasks=len(task_groups) or len({ep.get("task_id") for ep in episodes}),
      api_base="",
      default_annotator="abdoul",
    ),
    encoding="utf-8",
  )
  return packet_dir


def _index_side_nav(episode_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
  seen: dict[str, dict[str, Any]] = {}
  order: list[str] = []
  for ep in episode_pages:
    tid = str(ep.get("task_id") or "")
    if not tid:
      continue
    if tid not in seen:
      order.append(tid)
      seen[tid] = {
        "domain": ep.get("domain", ""),
        "task_id": tid,
        "task_short": tid[:8],
        "instruction_preview": (ep.get("instruction") or "")[:120],
        "href": ep["href"],
      }
    elif ep.get("model") == "a3b":
      seen[tid]["href"] = ep["href"]
  return [seen[tid] for tid in order]


def _enrich_task_groups(
  task_groups: list[dict[str, Any]],
  episode_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
  by_key = {(p["model"], p["task_id"]): p for p in episode_pages}
  if not task_groups:
    # synthesize from pages
    groups: dict[str, dict[str, Any]] = {}
    for p in episode_pages:
      tid = p["task_id"]
      g = groups.setdefault(
        tid,
        {"domain": p["domain"], "task_id": tid, "models": {}, "oracle_status": "pending"},
      )
      g["models"][p["model"]] = {
        "episode_id": p["episode_id"],
        "provisional_primary": p.get("provisional_primary"),
        "t_star": p.get("t_star"),
        "href": p["href"],
        "oracle_status": p.get("oracle_status", "pending"),
      }
      # prefer ready > partial > failed > pending
      status = str(p.get("oracle_status") or "pending")
      rank = {"ready": 3, "partial": 2, "failed": 1, "pending": 0}
      if rank.get(status, 0) >= rank.get(str(g.get("oracle_status") or "pending"), 0):
        g["oracle_status"] = status
    return list(groups.values())

  enriched = []
  for group in task_groups:
    g = dict(group)
    models = dict(g.get("models") or {})
    best = "pending"
    rank = {"ready": 3, "partial": 2, "failed": 1, "pending": 0}
    for model, info in list(models.items()):
      info = dict(info or {})
      page = by_key.get((model, g.get("task_id")))
      if page:
        info.setdefault("href", page["href"])
        info["oracle_status"] = page.get("oracle_status", "pending")
        status = str(info["oracle_status"])
        if rank.get(status, 0) >= rank.get(best, 0):
          best = status
      models[model] = info
    g["models"] = models
    g["oracle_status"] = best
    enriched.append(g)
  return enriched


def build_review_packet(
  manifest_path: Path,
  *,
  zip_paths: dict[str, Path],
  output_dir: Path,
  template_dir: Path,
  stratified_tasks: Path | None = None,
  select_turns: dict[str, str] | None = None,
  oracle_root: Path | None = None,
) -> Path:
  """Build index + per-episode HTML from ``manifest.json`` and HF zips.

  ``zip_paths`` maps model slug (``a3b``, ``7b``) to local zip path.
  """
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  episodes: list[dict[str, Any]] = manifest.get("episodes", [])
  output_dir.mkdir(parents=True, exist_ok=True)
  select_turns = select_turns or {}
  taxonomy_leaves = sorted({leaf.value for leaf in ALL_LEAVES})
  _copy_static_assets(template_dir, output_dir)
  oracle_root = _resolve_oracle_root(oracle_root)

  labels_path = output_dir / "annotations.json"
  if not labels_path.exists():
    labels_path.write_text(
      json.dumps(_empty_annotations(manifest.get("packet_id", "")), indent=2),
      encoding="utf-8",
    )

  episode_pages: list[dict[str, Any]] = []
  zf_cache: dict[str, zipfile.ZipFile] = {}
  bundle_cache: dict[tuple[str, str], dict[str, list[str]]] = {}

  try:
    for idx, ep in enumerate(episodes):
      model = ep["model"]
      episode_id = ep["episode_id"]
      slug = episode_slug(episode_id)
      rel_dir = Path(model) / slug
      episode_dir = output_dir / rel_dir
      episode_dir.mkdir(parents=True, exist_ok=True)

      zip_path = zip_paths.get(model)
      if zip_path is None:
        raise KeyError(f"No zip path for model {model!r}")

      if model not in zf_cache:
        zf_cache[model] = zipfile.ZipFile(zip_path)
      zf = zf_cache[model]

      cache_key = (model, ep.get("run_dir", ""))
      if cache_key not in bundle_cache:
        turn = select_turns.get(model)
        bundles = group_opencua_episodes(zf, select_turn=turn)
        bundle_cache[cache_key] = {b.episode_id: b.members for b in bundles}
      members = bundle_cache[cache_key].get(episode_id)
      if members is None:
        raise KeyError(f"Episode {episode_id} not found in zip for {model}")

      assets = build_episode_assets(
        zf,
        episode_id,
        members,
        episode_dir,
        select_turn=select_turns.get(model),
      )

      ctx, page_meta = _episode_render_ctx(
        manifest=manifest,
        ep=ep,
        assets=assets,
        idx=idx,
        episodes=episodes,
        taxonomy_leaves=taxonomy_leaves,
        stratified_tasks=stratified_tasks,
        oracle_root=oracle_root,
      )
      (episode_dir / "episode.html").write_text(
        _render_template(template_dir, "episode.html.j2", **ctx),
        encoding="utf-8",
      )
      episode_pages.append(page_meta)

    task_groups = _enrich_task_groups(manifest.get("task_groups") or [], episode_pages)
    (output_dir / "index.html").write_text(
      _render_template(
        template_dir,
        "index.html.j2",
        packet_id=manifest.get("packet_id", ""),
        episodes=episode_pages,
        task_groups=task_groups,
        side_nav=_index_side_nav(episode_pages),
        n_episodes=len(episode_pages),
        n_tasks=len(task_groups) or len({ep.get("task_id") for ep in episodes}),
        api_base="",
        default_annotator="abdoul",
      ),
      encoding="utf-8",
    )

    packet_manifest = {
      **manifest,
      "output_dir": str(output_dir),
      "oracle_root": str(oracle_root) if oracle_root else "",
      "episodes": [
        {
          **ep,
          "episode_html": episode_pages[i]["href"],
          "oracle_status": episode_pages[i].get("oracle_status", "pending"),
        }
        for i, ep in enumerate(episodes)
      ],
    }
    (output_dir / "packet_manifest.json").write_text(
      json.dumps(packet_manifest, indent=2), encoding="utf-8"
    )
  finally:
    for zf in zf_cache.values():
      zf.close()

  return output_dir


def escape_preview(text: str, limit: int = 120) -> str:
  """Short plain-text preview for tests."""
  cleaned = re.sub(r"\s+", " ", text).strip()
  if len(cleaned) > limit:
    return cleaned[: limit - 3] + "..."
  return cleaned
