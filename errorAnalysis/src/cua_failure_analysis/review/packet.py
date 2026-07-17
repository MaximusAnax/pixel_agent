"""Build static HTML trace review packets from HF trajectory zips."""

from __future__ import annotations

import json
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
from cua_failure_analysis.review.labels import judge_modes_ordered, label_storage_key
from cua_failure_analysis.taxonomy import ALL_LEAVES

STEP_SCREENSHOT_RE = re.compile(r"^step_(\d+)_", re.I)

# Written into human (OSWorld-Human guided replay) episode dirs so
# refresh_review_packet_html can re-render them without the gold run dir.
HUMAN_STEPS_FILE = "human_steps.json"


@dataclass
class ParsedStep:
  step_num: int
  action: str
  thought: str
  action_section: str
  code: str
  screenshot_file: str | None
  reward: Any
  done: bool


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
    code_match = re.search(r"```python\s*(.*?)```", response, re.S | re.I)
    steps.append(
      ParsedStep(
        step_num=step_num,
        action=action_raw,
        thought=thought_match.group(1).strip() if thought_match else response[:2000],
        action_section=action_match.group(1).strip() if action_match else "",
        code=code_match.group(1).strip() if code_match else "",
        screenshot_file=str(record.get("screenshot_file") or "") or None,
        reward=record.get("reward"),
        done=bool(record.get("done")),
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
    "success": success,
    "result_raw": result_path.read_text(encoding="utf-8", errors="replace").strip()
    if result_path.exists()
    else "",
    "steps": steps,
    "screenshot_by_step": screenshot_by_step,
    "select_turn": select_turn,
  }


def _downscale_screenshot(src: Path, dst: Path, *, max_side: int = 1600, quality: int = 80) -> bool:
  """Write a downscaled JPEG copy of ``src`` to ``dst`` (skip if it exists)."""
  if dst.exists():
    return True
  try:
    from PIL import Image
  except ImportError as exc:
    raise ImportError("Pillow is required for human replay episodes; pip install Pillow") from exc
  try:
    img = Image.open(src).convert("RGB")
  except OSError:
    return False
  w, h = img.size
  scale = max_side / max(w, h)
  if scale < 1.0:
    img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
  dst.parent.mkdir(parents=True, exist_ok=True)
  img.save(dst, "JPEG", quality=quality)
  return True


def build_human_episode_assets(
  gold_dir: Path,
  episode_dir: Path,
  *,
  episode_id: str,
) -> dict[str, Any]:
  """Build episode assets from an OSWorld-Human guided replay run directory.

  Gold replay layout (goldTrajectories pipeline): ``trace.jsonl`` with 0-based
  ``step`` records (``human_step``, ``verb``, ``coords``, ``action.command``),
  ``screenshots/stepNN_before.png`` observations plus ``final.png``, and
  ``manifest.json`` with ``success``/``score``/``instruction``.
  """
  trace_path = gold_dir / "trace.jsonl"
  if not trace_path.exists():
    raise FileNotFoundError(f"No trace.jsonl in {gold_dir}")
  records = [
    json.loads(line)
    for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if line.strip()
  ]

  gold_manifest: dict[str, Any] = {}
  manifest_path = gold_dir / "manifest.json"
  if manifest_path.exists():
    gold_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

  episode_dir.mkdir(parents=True, exist_ok=True)
  steps: list[ParsedStep] = []
  screenshot_by_step: dict[int, str] = {}

  for idx, rec in enumerate(records):
    raw_step = rec.get("step", idx)
    step_num = int(raw_step) + 1
    shot_name = None
    src = gold_dir / "screenshots" / f"step{int(raw_step):02d}_before.png"
    if src.exists() and _downscale_screenshot(src, episode_dir / f"step_{step_num}_before.jpg"):
      shot_name = f"step_{step_num}_before.jpg"
      screenshot_by_step[step_num] = shot_name

    coords = rec.get("coords")
    verb = rec.get("verb") or "?"
    action = f"{verb} @ {tuple(coords)}" if coords else verb
    code = str((rec.get("action") or {}).get("command") or "")
    if coords:
      code += (
        f"\n# grounded {str(rec.get('grounded_desc') or '')!r}"
        f" -> {tuple(coords)} (raw {rec.get('ground_raw')})"
      )
    steps.append(
      ParsedStep(
        step_num=step_num,
        action=action,
        thought=str(rec.get("human_step") or ""),
        action_section=str(rec.get("grounded_desc") or ""),
        code=code,
        screenshot_file=shot_name,
        reward=None,
        done=False,
      )
    )

  final_src = gold_dir / "screenshots" / "final.png"
  if final_src.exists():
    step_num = (steps[-1].step_num + 1) if steps else 1
    shot_name = f"step_{step_num}_final.jpg"
    if _downscale_screenshot(final_src, episode_dir / shot_name):
      screenshot_by_step[step_num] = shot_name
      steps.append(
        ParsedStep(
          step_num=step_num,
          action="(final screen at evaluation)",
          thought="Final state of the VM when the OSWorld evaluator ran.",
          action_section="",
          code="",
          screenshot_file=shot_name,
          reward=gold_manifest.get("score"),
          done=True,
        )
      )

  score = gold_manifest.get("score")
  result_raw = "" if score is None else f"{score:g} (OSWorld-Human guided replay)"
  assets = {
    "episode_id": episode_id,
    "success": gold_manifest.get("success"),
    "result_raw": result_raw,
    "steps": steps,
    "screenshot_by_step": screenshot_by_step,
    "select_turn": None,
  }
  (episode_dir / HUMAN_STEPS_FILE).write_text(
    json.dumps(
      {
        "episode_id": episode_id,
        "success": assets["success"],
        "result_raw": result_raw,
        "steps": [step.__dict__ for step in steps],
        "screenshot_by_step": screenshot_by_step,
      },
      indent=2,
    ),
    encoding="utf-8",
  )
  return assets


def _assets_from_episode_dir(episode_dir: Path, episode_id: str) -> dict[str, Any]:
  """Load traj + screenshots already on disk (no zip extraction)."""
  human_path = episode_dir / HUMAN_STEPS_FILE
  if human_path.exists():
    saved = json.loads(human_path.read_text(encoding="utf-8"))
    return {
      "episode_id": episode_id,
      "success": saved.get("success"),
      "result_raw": saved.get("result_raw", ""),
      "steps": [ParsedStep(**row) for row in saved.get("steps", [])],
      "screenshot_by_step": {int(k): v for k, v in saved.get("screenshot_by_step", {}).items()},
      "select_turn": None,
    }

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
    "success": success,
    "result_raw": result_path.read_text(encoding="utf-8", errors="replace").strip()
    if result_path.exists()
    else "",
    "steps": steps,
    "screenshot_by_step": screenshot_by_step,
    "select_turn": None,
  }


def _instructions_by_task(episodes: list[dict[str, Any]]) -> dict[str, str]:
  """task_id -> first non-empty instruction across the task's episodes."""
  out: dict[str, str] = {}
  for ep in episodes:
    task_id = ep.get("task_id") or ep.get("episode_id", "").split("/", 1)[-1]
    if task_id and ep.get("instruction") and not out.get(task_id):
      out[task_id] = str(ep["instruction"])
  return out


def refresh_review_packet_html(
  packet_dir: Path,
  *,
  template_dir: Path,
  stratified_tasks: Path | None = None,
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

  episode_pages: list[dict[str, Any]] = []
  for idx, ep in enumerate(episodes):
    model = ep["model"]
    episode_id = ep["episode_id"]
    slug = episode_slug(episode_id)
    episode_dir = packet_dir / model / slug
    assets = _assets_from_episode_dir(episode_dir, episode_id)

    task_id = ep.get("task_id") or episode_id.split("/", 1)[-1]
    instruction = ep.get("instruction") or _load_instruction(stratified_tasks, task_id)
    judge_modes = judge_modes_ordered(ep)
    sibling_href = ep.get("sibling_href") or ""
    sibling_model = "7b" if model == "a3b" else "a3b" if sibling_href else ""
    siblings = ep.get("siblings") or (
      [{"href": sibling_href, "model": sibling_model}] if sibling_href else []
    )
    label_key = label_storage_key(model, episode_id)

    step_rows = []
    t_star = ep.get("t_star")
    for step in assets["steps"]:
      shot = assets["screenshot_by_step"].get(step.step_num)
      step_rows.append(
        {
          "step_num": step.step_num,
          "action": step.action,
          "thought": step.thought,
          "action_section": step.action_section,
          "code": step.code,
          "reward": step.reward,
          "done": step.done,
          "screenshot": shot,
          "is_t_star": t_star is not None and step.step_num == int(t_star),
        }
      )

    prev_link = next_link = None
    if idx > 0:
      prev_slug = episode_slug(episodes[idx - 1]["episode_id"])
      prev_link = f"../../{episodes[idx - 1]['model']}/{prev_slug}/episode.html"
    if idx + 1 < len(episodes):
      next_slug = episode_slug(episodes[idx + 1]["episode_id"])
      next_link = f"../../{episodes[idx + 1]['model']}/{next_slug}/episode.html"

    html_path = episode_dir / "episode.html"
    html_path.write_text(
      _render_template(
        template_dir,
        "episode.html.j2",
        packet_id=manifest.get("packet_id", ""),
        model=model,
        episode_id=episode_id,
        domain=ep.get("domain", ""),
        task_id=task_id,
        instruction=instruction,
        success=assets["success"],
        result_raw=assets["result_raw"],
        provisional_primary=ep.get("provisional_primary", ""),
        judge_modes_ordered=judge_modes,
        secondary_modes=ep.get("secondary_modes") or [],
        propagated=ep.get("propagated", False),
        t_star=t_star,
        evidence=ep.get("evidence", ""),
        confidence=ep.get("confidence"),
        tier_used=ep.get("tier_used"),
        steps=step_rows,
        prev_link=prev_link,
        next_link=next_link,
        index_href="../../index.html",
        sibling_href=sibling_href,
        sibling_model=sibling_model,
        siblings=siblings,
        label_key=label_key,
        taxonomy_leaves=taxonomy_leaves,
        api_base="",
        default_annotator="abdoul",
      ),
      encoding="utf-8",
    )

    episode_pages.append(
      {
        "model": model,
        "domain": ep.get("domain", ""),
        "task_id": task_id,
        "episode_id": episode_id,
        "provisional_primary": ep.get("provisional_primary", ""),
        "t_star": t_star,
        "confusing": ep.get("confusing", False),
        "href": f"{model}/{slug}/episode.html",
      }
    )

  task_groups = manifest.get("task_groups") or []
  (packet_dir / "index.html").write_text(
    _render_template(
      template_dir,
      "index.html.j2",
      packet_id=manifest.get("packet_id", ""),
      episodes=episode_pages,
      task_groups=task_groups,
      n_episodes=len(episode_pages),
      n_tasks=len(task_groups) or len({ep.get("task_id") for ep in episodes}),
      instructions=_instructions_by_task(episodes),
      api_base="",
      default_annotator="abdoul",
    ),
    encoding="utf-8",
  )
  return packet_dir


def build_review_packet(
  manifest_path: Path,
  *,
  zip_paths: dict[str, Path],
  output_dir: Path,
  template_dir: Path,
  stratified_tasks: Path | None = None,
  select_turns: dict[str, str] | None = None,
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

  labels_path = output_dir / "annotations.json"
  if not labels_path.exists():
    labels_path.write_text(
      json.dumps(_empty_annotations(manifest.get("packet_id", "")), indent=2),
      encoding="utf-8",
    )

  episode_pages: list[dict[str, Any]] = []
  zf_cache: dict[str, zipfile.ZipFile] = {}
  bundle_cache: dict[tuple[str, str], list[str]] = {}

  try:
    for idx, ep in enumerate(episodes):
      model = ep["model"]
      episode_id = ep["episode_id"]
      slug = episode_slug(episode_id)
      rel_dir = Path(model) / slug
      episode_dir = output_dir / rel_dir
      episode_dir.mkdir(parents=True, exist_ok=True)

      gold_dir = ep.get("gold_dir")
      if gold_dir:
        assets = build_human_episode_assets(
          Path(gold_dir), episode_dir, episode_id=episode_id
        )
      else:
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
          bundle_cache[cache_key] = {
            b.episode_id: b.members for b in bundles
          }
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

      task_id = ep.get("task_id") or episode_id.split("/", 1)[-1]
      instruction = ep.get("instruction") or _load_instruction(stratified_tasks, task_id)
      judge_modes = judge_modes_ordered(ep)
      sibling_href = ep.get("sibling_href") or ""
      sibling_model = "7b" if model == "a3b" else "a3b" if sibling_href else ""
      siblings = ep.get("siblings") or (
        [{"href": sibling_href, "model": sibling_model}] if sibling_href else []
      )
      label_key = label_storage_key(model, episode_id)

      step_rows = []
      t_star = ep.get("t_star")
      for step in assets["steps"]:
        shot = assets["screenshot_by_step"].get(step.step_num)
        step_rows.append(
          {
            "step_num": step.step_num,
            "action": step.action,
            "thought": step.thought,
            "action_section": step.action_section,
            "code": step.code,
            "reward": step.reward,
            "done": step.done,
            "screenshot": shot,
            "is_t_star": t_star is not None and step.step_num == int(t_star),
          }
        )

      html_path = episode_dir / "episode.html"
      prev_link = None
      next_link = None
      if idx > 0:
        prev_slug = episode_slug(episodes[idx - 1]["episode_id"])
        prev_link = f"../../{episodes[idx - 1]['model']}/{prev_slug}/episode.html"
      if idx + 1 < len(episodes):
        next_slug = episode_slug(episodes[idx + 1]["episode_id"])
        next_link = f"../../{episodes[idx + 1]['model']}/{next_slug}/episode.html"

      episode_html = _render_template(
        template_dir,
        "episode.html.j2",
        packet_id=manifest.get("packet_id", ""),
        model=model,
        episode_id=episode_id,
        domain=ep.get("domain", ""),
        task_id=task_id,
        instruction=instruction,
        success=assets["success"],
        result_raw=assets["result_raw"],
        provisional_primary=ep.get("provisional_primary", ""),
        judge_modes_ordered=judge_modes,
        secondary_modes=ep.get("secondary_modes") or [],
        propagated=ep.get("propagated", False),
        t_star=t_star,
        evidence=ep.get("evidence", ""),
        confidence=ep.get("confidence"),
        tier_used=ep.get("tier_used"),
        steps=step_rows,
        prev_link=prev_link,
        next_link=next_link,
        index_href="../../index.html",
        sibling_href=sibling_href,
        sibling_model=sibling_model,
        siblings=siblings,
        label_key=label_key,
        taxonomy_leaves=taxonomy_leaves,
        api_base="",
        default_annotator="abdoul",
      )
      html_path.write_text(episode_html, encoding="utf-8")

      episode_pages.append(
        {
          "model": model,
          "domain": ep.get("domain", ""),
          "task_id": task_id,
          "episode_id": episode_id,
          "provisional_primary": ep.get("provisional_primary", ""),
          "t_star": t_star,
          "confusing": ep.get("confusing", False),
          "href": f"{model}/{slug}/episode.html",
        }
      )

    task_groups = manifest.get("task_groups") or []
    index_html = _render_template(
      template_dir,
      "index.html.j2",
      packet_id=manifest.get("packet_id", ""),
      episodes=episode_pages,
      task_groups=task_groups,
      n_episodes=len(episode_pages),
      n_tasks=len(task_groups) or len({ep.get("task_id") for ep in episodes}),
      instructions=_instructions_by_task(episodes),
      api_base="",
      default_annotator="abdoul",
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    packet_manifest = {
      **manifest,
      "output_dir": str(output_dir),
      "episodes": [
        {**ep, "episode_html": episode_pages[i]["href"]} for i, ep in enumerate(episodes)
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
