"""Shared helpers for ops/meetings/ date folders and artifact paths."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
REPO_ROOT = OPS_DIR.parent  # pixelAgent/ (git root)
MEETINGS_DIR = OPS_DIR / "meetings"
CONFIG_DIR = OPS_DIR / "config"

_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def meeting_dir(date: dt.date) -> Path:
    return MEETINGS_DIR / date.isoformat()


def ensure_meeting_dir(date: dt.date) -> Path:
    d = meeting_dir(date)
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_doc_id(value: str) -> str:
    """Accept a raw doc id or a Google Docs/Drive URL."""
    value = value.strip()
    m = re.search(r"/document/d/([a-zA-Z0-9_-]+)", value)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", value)
    if m:
        return m.group(1)
    return value


def load_meetings_env() -> dict[str, str]:
    """Load ops/config/meetings.env (KEY=VALUE, # comments)."""
    path = CONFIG_DIR / "meetings.env"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def write_meta(meeting: Path, **fields: str) -> None:
    meta_path = meeting / "meta.json"
    meta: dict[str, str] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            meta = {}
    meta.update({k: v for k, v in fields.items() if v})
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")


def list_meeting_dirs(limit: int = 0) -> list[Path]:
    dirs = [
        d for d in MEETINGS_DIR.iterdir()
        if d.is_dir() and _DATE_DIR_RE.match(d.name)
    ]
    dirs.sort(key=lambda d: d.name)
    if limit > 0:
        return dirs[-limit:]
    return dirs
