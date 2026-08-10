#!/usr/bin/env python3
"""Generate compact evaluator.func markdown summaries for vendored pilot tasks.

Scans config/osworld/<pin>/tasks for unique evaluator.func values, downloads the
matching OSWorld metrics source at the pinned SHA, and writes
config/osworld/<pin>/eval_summaries/<func>.md.

Usage (from errorAnalysis/):
  python scripts/generate_eval_summaries.py
"""

from __future__ import annotations

import argparse
import ast
import json
import textwrap
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DEFAULT_SOURCES = CONFIG / "osworld_sources.yaml"

METRICS_MODULES = [
  "basic_os.py",
  "chrome.py",
  "docs.py",
  "general.py",
  "gimp.py",
  "libreoffice.py",
  "others.py",
  "pdf.py",
  "slides.py",
  "table.py",
  "thunderbird.py",
  "vlc.py",
  "vscode.py",
]

# Hand-curated purpose lines for dense / common funcs (override auto docstring).
HAND_CURATED: dict[str, dict[str, str]] = {
  "is_expected_tabs": {
    "purpose": "Check that Chrome open-tab URLs match the expected URL list (order-sensitive via are_lists_equal + compare_urls).",
    "inputs": "open_tabs (list of {url,...} from get_open_tabs_info); rule with type=url and urls=[...].",
    "matching_rules": "Returns 1.0 iff expected and actual URL lists are equal under compare_urls; else 0.0.",
    "pitfalls": "Trailing slashes / www / redirects can fail compare_urls; empty open_tabs → 0.0; order matters.",
  },
  "compare_table": {
    "purpose": "Compare LibreOffice Calc spreadsheet content against a gold sheet using rule-driven checks (cells, ranges, structure).",
    "inputs": "Predicted and gold spreadsheet paths (via getters); options/rules from evaluator.expected.",
    "matching_rules": "Aggregates per-rule sheet comparisons; typically returns a float score in [0, 1].",
    "pitfalls": "Dense rule sets; small formatting/value drift fails; prefer reading expected rules in the task JSON.",
  },
  "compare_docx_files": {
    "purpose": "Compare two .docx documents for content equivalence under configured ignore options.",
    "inputs": "Predicted and gold docx paths; optional kwargs for ignoring newlines / styles.",
    "matching_rules": "Returns 1.0 on match, 0.0 otherwise (implementation-specific tolerances).",
    "pitfalls": "Whitespace and style differences; image embeds; revision marks.",
  },
}

GETTER_ALIASES: dict[str, str] = {
  "open_tabs_info": "get_open_tabs_info",
  "active_tab_info": "get_active_tab_info",
  "vm_file": "get_vm_file",
  "cloud_file": "get_cloud_file",
  "cache_file": "get_cache_file",
  "content_from_vm_file": "get_content_from_vm_file",
  "accessibility_tree": "get_accessibility_tree",
  "rule": "get_rule",
}


def _fetch(url: str, *, retries: int = 3) -> str:
  last_err: Exception | None = None
  headers = {"User-Agent": "pixelAgent-eval-summaries/1.0"}
  for attempt in range(retries):
    try:
      with httpx.Client(timeout=60.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
      last_err = exc
      time.sleep(0.4 * (attempt + 1))
  raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def _collect_funcs(tasks_root: Path) -> dict[str, dict]:
  """func_name -> {result_types: set, task_ids: list}."""
  info: dict[str, dict] = {}
  for path in sorted(tasks_root.glob("*/*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    evaluator = data.get("evaluator") or {}
    funcs = evaluator.get("func")
    if isinstance(funcs, str):
      func_list = [funcs]
    elif isinstance(funcs, list):
      func_list = [str(f) for f in funcs if f]
    else:
      continue
    result = evaluator.get("result") or {}
    result_types: list[str] = []
    if isinstance(result, dict) and result.get("type"):
      result_types.append(str(result["type"]))
    elif isinstance(result, list):
      for item in result:
        if isinstance(item, dict) and item.get("type"):
          result_types.append(str(item["type"]))
    for func in func_list:
      slot = info.setdefault(func, {"result_types": set(), "task_ids": []})
      slot["result_types"].update(result_types)
      slot["task_ids"].append(path.stem)
  return info


def _extract_function_source(module_src: str, func_name: str) -> tuple[str | None, str | None]:
  """Return (source, docstring) for func_name using AST."""
  try:
    tree = ast.parse(module_src)
  except SyntaxError:
    return None, None
  for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
      segment = ast.get_source_segment(module_src, node)
      doc = ast.get_docstring(node)
      return segment, doc
  return None, None


def _find_func_in_modules(
  func_name: str,
  modules: dict[str, str],
) -> tuple[str | None, str | None, str | None]:
  for name, src in modules.items():
    segment, doc = _extract_function_source(src, func_name)
    if segment:
      return name, segment, doc
  return None, None, None


def _getter_line(result_types: set[str]) -> str:
  parts: list[str] = []
  for rt in sorted(result_types):
    getter = GETTER_ALIASES.get(rt, f"get_{rt}" if not rt.startswith("get_") else rt)
    parts.append(f"{rt} → {getter}")
  return "; ".join(parts) if parts else "(no result.type on pilot tasks using this func)"


def _render_summary(
  func_name: str,
  *,
  module_name: str | None,
  source: str | None,
  docstring: str | None,
  result_types: set[str],
  task_ids: list[str],
  osworld_commit: str,
) -> str:
  curated = HAND_CURATED.get(func_name, {})
  purpose = curated.get("purpose") or (docstring or "").strip() or "(no docstring; see source excerpt)"
  inputs = curated.get("inputs") or "See function signature and task evaluator.result / expected."
  matching = curated.get("matching_rules") or "See return value in source (typically 0.0 / 1.0 or [0,1] score)."
  pitfalls = curated.get("pitfalls") or "Confirm expected rules in the task JSON; empty getter results often score 0."

  excerpt = ""
  if source:
    # Cap excerpt length for judge context.
    lines = source.splitlines()
    if len(lines) > 80:
      excerpt = "\n".join(lines[:80]) + "\n# ... truncated ...\n"
    else:
      excerpt = source
  else:
    excerpt = f"# Function {func_name} not found in metrics modules at this pin."

  body = f"""# `{func_name}`

## Purpose
{purpose}

## Inputs
{inputs}

## Matching rules
{matching}

## Common pitfalls
{pitfalls}

## Pilot usage
- Tasks ({len(task_ids)}): {", ".join(task_ids[:12])}{"…" if len(task_ids) > 12 else ""}
- Metrics module: `{module_name or "unknown"}`
- OSWorld commit: `{osworld_commit}`

## Getter mapping
{_getter_line(result_types)}

## Source excerpt
```python
{excerpt}
```
"""
  return textwrap.dedent(body).strip() + "\n"


def generate(*, sources_path: Path = DEFAULT_SOURCES, pin: str | None = None) -> Path:
  sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
  pin_name = pin or str(sources["pin"])
  osw = sources["osworld"]
  pin_dir = CONFIG / "osworld" / pin_name
  tasks_root = pin_dir / "tasks"
  if not tasks_root.exists():
    raise SystemExit(f"Missing vendored tasks at {tasks_root}; run vendor_osworld_metadata.py first")

  func_info = _collect_funcs(tasks_root)
  print(f"Found {len(func_info)} unique evaluator.func values under {tasks_root}")

  modules: dict[str, str] = {}
  for mod in METRICS_MODULES:
    url = (
      f"https://raw.githubusercontent.com/{osw['repo']}/{osw['commit']}/"
      f"{osw['metrics_dir']}/{mod}"
    )
    try:
      modules[mod] = _fetch(url)
      print(f"  cached metrics/{mod}")
      time.sleep(0.1)
    except Exception as exc:
      print(f"  WARN skip {mod}: {exc}")

  out_dir = pin_dir / "eval_summaries"
  out_dir.mkdir(parents=True, exist_ok=True)
  for func_name, meta in sorted(func_info.items()):
    module_name, source, doc = _find_func_in_modules(func_name, modules)
    md = _render_summary(
      func_name,
      module_name=module_name,
      source=source,
      docstring=doc,
      result_types=set(meta["result_types"]),
      task_ids=list(meta["task_ids"]),
      osworld_commit=str(osw["commit"]),
    )
    out_path = out_dir / f"{func_name}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"  wrote {out_path.relative_to(ROOT)}")

  index = {
    "pin": pin_name,
    "func_count": len(func_info),
    "funcs": sorted(func_info.keys()),
  }
  (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
  return out_dir


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
  parser.add_argument("--pin", default=None)
  args = parser.parse_args()
  generate(sources_path=args.sources, pin=args.pin)


if __name__ == "__main__":
  main()
