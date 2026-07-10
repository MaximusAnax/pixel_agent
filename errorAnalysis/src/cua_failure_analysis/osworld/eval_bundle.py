"""Format OSWorld evaluator context for judge prompts and review UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cua_failure_analysis.osworld.metadata import resolve_pin_dir

# Common result.type → getter name (OSWorld convention: get_<type>).
GETTER_ALIASES: dict[str, str] = {
  "open_tabs_info": "get_open_tabs_info",
  "active_tab_info": "get_active_tab_info",
  "vm_file": "get_vm_file",
  "cloud_file": "get_cloud_file",
  "cache_file": "get_cache_file",
  "content_from_vm_file": "get_content_from_vm_file",
  "accessibility_tree": "get_accessibility_tree",
  "rule": "get_rule",
  "vm_command_line": "get_vm_command_line",
}


def getter_name_for_result_type(result_type: str | None) -> str | None:
  if not result_type:
    return None
  if result_type in GETTER_ALIASES:
    return GETTER_ALIASES[result_type]
  if result_type.startswith("get_"):
    return result_type
  return f"get_{result_type}"


def _summarize_setup(config: list[Any] | None, max_items: int = 6) -> str:
  if not config:
    return "(none)"
  lines: list[str] = []
  for item in config[:max_items]:
    if not isinstance(item, dict):
      continue
    kind = item.get("type", "?")
    params = item.get("parameters") or {}
    if kind == "launch":
      cmd = params.get("command")
      if isinstance(cmd, list):
        lines.append(f"- launch: {' '.join(str(c) for c in cmd[:4])}")
      else:
        lines.append(f"- launch: {cmd}")
    elif kind in {"chrome_open_tabs", "chrome_close_tabs"}:
      key = "urls_to_open" if "open" in kind else "urls_to_close"
      urls = params.get(key) or []
      lines.append(f"- {kind}: {urls}")
    elif kind == "download":
      lines.append(f"- download: {params.get('files') or params.get('url') or '...'}")
    elif kind == "open":
      lines.append(f"- open: {params.get('path') or params}")
    else:
      brief = json.dumps(params, ensure_ascii=False)
      if len(brief) > 120:
        brief = brief[:117] + "..."
      lines.append(f"- {kind}: {brief}")
  if len(config) > max_items:
    lines.append(f"- … ({len(config) - max_items} more setup steps)")
  return "\n".join(lines) if lines else "(none)"


def _success_criteria(evaluator: dict[str, Any]) -> str:
  expected = evaluator.get("expected")
  if expected is None:
    return "(see evaluator.func / expected gold file)"
  if isinstance(expected, dict):
    rules = expected.get("rules")
    if isinstance(rules, dict):
      if rules.get("type") == "url" and "urls" in rules:
        return f"open tabs must include {rules['urls']}"
      if "url" in rules:
        return f"active tab URL must match {rules['url']}"
      return json.dumps(rules, ensure_ascii=False)[:400]
    return json.dumps(expected, ensure_ascii=False)[:400]
  return str(expected)[:400]


def _load_func_summary(func_name: str, pin_dir: Path) -> str:
  path = pin_dir / "eval_summaries" / f"{func_name}.md"
  if not path.exists():
    return f"(no summary vendored for {func_name})"
  text = path.read_text(encoding="utf-8").strip()
  # Prefer the prose body before a long source excerpt.
  if "## Source excerpt" in text:
    text = text.split("## Source excerpt", 1)[0].strip()
  if len(text) > 1200:
    text = text[:1197] + "..."
  return text


def format_eval_bundle(
  task_json: dict[str, Any],
  *,
  outcome: str | None = None,
  result_txt: float | str | None = None,
  func_summary_path: Path | str | None = None,
  pin_dir: Path | None = None,
) -> str:
  """Build the judge/UI eval context string for one task.

  Args:
    task_json: Vendored OSWorld task JSON (may include `_domain`).
    outcome: Optional override like "fail" / "pass".
    result_txt: Optional HF result.txt value (0.0 / 1.0).
    func_summary_path: Optional path to a specific summary markdown file.
    pin_dir: Vendored pin root (defaults to configured pin).
  """
  root = pin_dir or resolve_pin_dir()
  instruction = str(task_json.get("instruction") or "").strip()
  evaluator = task_json.get("evaluator") or {}
  func = evaluator.get("func")
  if isinstance(func, list):
    func_name = ", ".join(str(f) for f in func)
    primary_func = str(func[0]) if func else ""
  else:
    func_name = str(func or "")
    primary_func = func_name

  result_block = evaluator.get("result") or {}
  result_type = None
  if isinstance(result_block, dict):
    result_type = result_block.get("type")
  elif isinstance(result_block, list) and result_block:
    first = result_block[0]
    if isinstance(first, dict):
      result_type = first.get("type")

  getter = getter_name_for_result_type(str(result_type) if result_type else None)

  if outcome is None and result_txt is not None:
    try:
      outcome = "pass" if float(result_txt) >= 1.0 else "fail"
    except (TypeError, ValueError):
      outcome = str(result_txt)
  outcome_str = outcome or "unknown"
  result_note = ""
  if result_txt is not None:
    result_note = f" (result.txt={result_txt})"

  postconfig = task_json.get("postconfig")
  postconfig_note = ""
  if postconfig:
    postconfig_note = json.dumps(postconfig, ensure_ascii=False)[:300]

  if func_summary_path is not None:
    summary_path = Path(func_summary_path)
    summary = (
      summary_path.read_text(encoding="utf-8").strip()
      if summary_path.exists()
      else f"(missing {summary_path})"
    )
    if "## Source excerpt" in summary:
      summary = summary.split("## Source excerpt", 1)[0].strip()
  elif primary_func:
    summary = _load_func_summary(primary_func, root)
  else:
    summary = "(no evaluator.func)"

  lines = [
    f"OSWorld outcome: {outcome_str}{result_note}",
    f"Canonical instruction: {instruction}",
    "Setup (summary):",
    _summarize_setup(task_json.get("config")),
  ]
  if postconfig_note:
    lines.append(f"Postconfig note: {postconfig_note}")
  lines.extend(
    [
      f"Success criteria: {_success_criteria(evaluator)}",
      f"Evaluator function: {func_name or '(none)'}",
      f"Getter: {result_type or '(none)'} → {getter or '(none)'}",
      "Function semantics:",
      summary,
    ]
  )
  return "\n".join(lines).strip() + "\n"
