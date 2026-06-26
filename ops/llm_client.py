"""LLM client for ops/ scripts (stdlib only).

Default provider: **Anthropic** when `ANTHROPIC_API_KEY` is set (or in
`ops/config/meetings.env`). OpenAI-compatible endpoints remain available via
`STATE_LLM_PROVIDER=openai` for legacy setups.

Environment (also loadable from ops/config/meetings.env):
  ANTHROPIC_API_KEY       — Anthropic API key (preferred)
  STATE_LLM_MODEL         — optional override (default: claude-sonnet-4-6)
  STATE_LLM_PROVIDER      — force `anthropic` or `openai`
  STATE_LLM_API_KEY       — generic key override
  STATE_LLM_BASE_URL      — OpenAI-compatible base URL (openai provider only)
  OPENAI_API_KEY          — fallback for openai provider
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from meeting_lib import load_meetings_env  # noqa: E402

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def apply_meetings_env() -> None:
    """Overlay ops/config/meetings.env into os.environ (does not override set vars)."""
    for key, val in load_meetings_env().items():
        if val and key not in os.environ:
            os.environ[key] = val


def llm_config() -> dict | None:
    """Return provider config dict or None if no key is available."""
    apply_meetings_env()
    provider = os.environ.get("STATE_LLM_PROVIDER", "").strip().lower()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    generic_key = os.environ.get("STATE_LLM_API_KEY")

    if not provider:
        if anthropic_key:
            provider = "anthropic"
        elif openai_key:
            provider = "openai"
        elif generic_key:
            provider = "anthropic"  # project default

    if provider == "anthropic":
        key = anthropic_key or generic_key
        if not key:
            return None
        return {
            "provider": "anthropic",
            "key": key,
            "model": os.environ.get("STATE_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL),
        }

    key = openai_key or generic_key
    if not key:
        return None
    return {
        "provider": "openai",
        "key": key,
        "base_url": os.environ.get("STATE_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("STATE_LLM_MODEL", DEFAULT_OPENAI_MODEL),
    }


def _https_context() -> ssl.SSLContext:
    """CA bundle for HTTPS. certifi fixes macOS python.org CERTIFICATE_VERIFY_FAILED."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _urlopen(req: urllib.request.Request, timeout: int):
    return urllib.request.urlopen(req, timeout=timeout, context=_https_context())


def complete(cfg: dict, system: str, user: str, *, max_tokens: int = 8192) -> str:
    if cfg["provider"] == "anthropic":
        return _anthropic_complete(cfg, system, user, max_tokens=max_tokens)
    return _openai_complete(cfg, system, user, max_tokens=max_tokens)


def _anthropic_complete(cfg: dict, system: str, user: str, *, max_tokens: int) -> str:
    payload = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": cfg["key"],
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with _urlopen(req, 300) as resp:
        data = json.loads(resp.read())
    blocks = data.get("content") or []
    texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text")]
    if not texts:
        raise KeyError("Anthropic response had no text content")
    return "\n".join(texts).strip()


def _openai_complete(cfg: dict, system: str, user: str, *, max_tokens: int) -> str:
    url = f"{cfg['base_url']}/chat/completions"
    payload = {
        "model": cfg["model"],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {cfg['key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with _urlopen(req, 300) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()
