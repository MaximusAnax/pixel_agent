"""Backend-agnostic helpers for the whole-trajectory judge.

Both the local (vLLM) and API (Anthropic) backends share:
  - normalized-failure I/O + resume bookkeeping,
  - screenshot selection/loading (image budget),
  - parsing/validation of the model output into the ``Classification`` schema
    (with the authoritative category derived from the primary mode),
  - the ``classifications.jsonl`` record shape.

Keeping this here means the two backends only differ in *how* they call the
model, not in what goes in or comes out — so their labels stay comparable.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from cua_failure_analysis.trajectory_judge.judge_prompt import select_screenshot_steps
from cua_failure_analysis.trajectory_judge.schema import Classification
from cua_failure_analysis.trajectory_judge.taxonomy import MODE_CATEGORY, FailureMode

DEFAULT_LOCAL_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
# Kept in sync with the per-step Anthropic judge default (judge/anthropic_client.py).
DEFAULT_API_MODEL = "claude-sonnet-4-6"


@dataclass
class JudgeOutput:
    """One backend's result for a single trajectory."""

    parsed: dict | None
    parse_ok: bool
    raw: str
    n_images: int
    usage: dict | None = None


def load_image(path: str, max_side: int = 1280) -> Image.Image | None:
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] could not open image {path}: {e}", file=sys.stderr)
        return None
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    return img


def uid_of(traj: dict) -> str:
    return f"{traj['model']}/{traj['domain']}/{traj['task_id']}"


def load_failures(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def already_done(out_path: Path) -> set[str]:
    """UIDs already present in an output file (for resumable runs)."""
    done: set[str] = set()
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                try:
                    done.add(json.loads(line)["uid"])
                except Exception:  # noqa: BLE001
                    pass
    return done


def stratified_head(trajs: list[dict], limit: int) -> list[dict]:
    """Take ~limit trajectories, round-robin across models then domains, so a
    validation/limited sample spans both agents and several domains.

    Deterministic (stable input order), so re-running with the same --limit
    selects the same subset — which keeps resume correct and keeps a
    ``--backend both`` run judging the *same* trajectories with local and API."""
    buckets: dict[tuple, deque] = defaultdict(deque)
    for t in trajs:
        buckets[(t["model"], t["domain"])].append(t)
    queues = list(buckets.values())
    out: list[dict] = []
    while len(out) < limit and any(queues):
        for q in queues:
            if q:
                out.append(q.popleft())
                if len(out) >= limit:
                    break
    return out


def select_images(traj: dict, max_images: int, max_side: int) -> tuple[list[int], list[Image.Image]]:
    """Choose which steps' screenshots to attach and load them (downscaled).

    Returns the kept step indices (in order) and the matching PIL images. The
    caller passes the indices to ``build_messages`` and supplies the images in
    the same order (as vLLM ``multi_modal_data`` or Anthropic image blocks)."""
    sel = select_screenshot_steps(traj, max_images)
    images: list[Image.Image] = []
    kept: list[int] = []
    for idx in sel:
        sp = next((s["screenshot_path"] for s in traj["steps"] if s["idx"] == idx), None)
        img = load_image(sp, max_side) if sp else None
        if img is not None:
            images.append(img)
            kept.append(idx)
    return kept, images


def _finalize(parsed: dict) -> dict:
    """The category is a deterministic function of the primary mode; trust the
    mode and derive the authoritative category, flagging any model mismatch."""
    mode = FailureMode(parsed["primary_failure_mode"])
    derived = MODE_CATEGORY[mode].value
    parsed["category_model"] = parsed.get("category")
    parsed["category"] = derived
    parsed["category_mismatch"] = parsed["category_model"] != derived
    return parsed


def parse_json_text(raw: str) -> tuple[dict, bool]:
    """Validate a raw JSON *string* against the Classification schema."""
    try:
        parsed = Classification.model_validate_json(raw).model_dump()
        return _finalize(parsed), True
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, False


def parse_json_obj(obj: dict) -> tuple[dict, bool]:
    """Validate an already-decoded JSON *object* (e.g. an Anthropic tool input)."""
    try:
        parsed = Classification.model_validate(obj).model_dump()
        return _finalize(parsed), True
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "raw_obj": obj}, False


def build_record(traj: dict, backend: str, model: str, out: JudgeOutput) -> dict:
    """The one line written to classifications.jsonl for this (traj, backend)."""
    rec = {
        "uid": uid_of(traj),
        "model": traj["model"],
        "domain": traj["domain"],
        "task_id": traj["task_id"],
        "reward": traj["reward"],
        "num_steps": traj["num_steps"],
        "n_images": out.n_images,
        "judge_backend": backend,
        "judge_model": model,
        "parse_ok": out.parse_ok,
        "classification": out.parsed,
        "raw": out.raw,
    }
    if out.usage is not None:
        rec["usage"] = out.usage
    return rec
