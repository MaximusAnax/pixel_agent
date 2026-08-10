"""Tests for trace review packet generation."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from cua_failure_analysis.review.labels import build_discovery_row, judge_modes_ordered
from cua_failure_analysis.review.packet import (
  build_human_episode_assets,
  build_human_stub_assets,
  build_review_packet,
  episode_slug,
  parse_traj_steps,
  refresh_review_packet_html,
)
from cua_failure_analysis.review.selection import (
  is_confusing_episode,
  load_offline_judge,
  select_from_pool,
  select_paired_all_episodes,
  select_paired_pilot_episodes,
  write_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures" / "opencua_a3b"
EPISODE_ID = "chrome/030eeff7-b492-4218-b312-701ec99ee0cc"
EPISODE_SLUG = episode_slug(EPISODE_ID)
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "trace_review"
ROOT = Path(__file__).resolve().parents[1]
A3B_RUN = ROOT / "data/babel_outputs/20260626_172919_a3b_pilot_full_v4"
B7_RUN = ROOT / "data/babel_outputs/20260626_172922_7b_pilot_full_v4"


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
  members = json.loads((FIXTURES / "zip_members_sample.json").read_text())
  traj_src = FIXTURES / "traj_failed.jsonl"
  zip_path = tmp_path / "sample.zip"
  with zipfile.ZipFile(zip_path, "w") as zf:
    zf.writestr(f"{EPISODE_ID}/traj.jsonl", traj_src.read_bytes())
    zf.writestr(f"{EPISODE_ID}/result.txt", b"0")
    for member in members:
      if member.endswith(".png"):
        zf.writestr(f"{EPISODE_ID}/{Path(member).name}", b"\x89PNG\r\n\x1a\n")
      elif member.endswith("recording.mp4"):
        zf.writestr(f"{EPISODE_ID}/recording.mp4", b"\x00\x00\x00\x18ftypmp42")
  return zip_path


def test_parse_traj_steps():
  steps = parse_traj_steps(FIXTURES / "traj_failed.jsonl")
  assert len(steps) >= 3
  assert "freeze" in steps[0].thought.lower()


def test_judge_modes_ordered():
  modes = judge_modes_ordered(
    {"provisional_primary": "Reasoning Drift", "secondary_modes": ["Goal Hallucination"]}
  )
  assert modes == ["Reasoning Drift", "Goal Hallucination"]


def test_select_paired_pilot_episodes():
  if not A3B_RUN.exists() or not B7_RUN.exists():
    pytest.skip("v4 pilot runs not synced locally")
  episodes, groups = select_paired_pilot_episodes(
    [A3B_RUN, B7_RUN],
    tasks_file=ROOT / "config/stratified_tasks.json",
    phase="pilot",
  )
  assert len(groups) == 30
  assert len(episodes) == 60
  task_ids = {ep["task_id"] for ep in episodes}
  assert len(task_ids) == 30
  assert sum(1 for ep in episodes if ep["model"] == "a3b") == 30
  assert sum(1 for ep in episodes if ep["model"] == "7b") == 30


def test_build_review_packet(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  manifest_path = tmp_path / "manifest.json"
  manifest_path.write_text(
    json.dumps(
      {
        "packet_id": "test_packet",
        "task_groups": [],
        "episodes": [
          {
            "model": "a3b",
            "episode_id": EPISODE_ID,
            "domain": "chrome",
            "task_id": "030eeff7-b492-4218-b312-701ec99ee0cc",
            "t_star": 2,
            "provisional_primary": "Reasoning Drift",
            "secondary_modes": ["Goal Hallucination"],
            "propagated": False,
            "evidence": "judge says X",
            "confidence": 0.7,
            "run_dir": str(tmp_path),
          }
        ],
      }
    ),
    encoding="utf-8",
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )
  index = (out / "index.html").read_text(encoding="utf-8")
  episode = (out / "a3b" / EPISODE_ID.replace("/", "__") / "episode.html").read_text(
    encoding="utf-8"
  )
  assert (out / "review.js").exists()
  assert (out / "review.css").exists()
  assert (out / "annotations.json").exists()
  assert "test_packet" in index
  assert "Judge reasoning" in episode
  assert "Reasoning Drift" in episode and "Goal Hallucination" in episode
  assert "human-reasoning" in episode
  assert "pipeline t*" in episode
  assert "judge says X" in episode


def test_episode_nav_links_resolve(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  slug = EPISODE_SLUG
  manifest_path = tmp_path / "manifest.json"
  manifest_path.write_text(
    json.dumps(
      {
        "packet_id": "nav_test",
        "task_groups": [],
        "episodes": [
          {
            "model": "a3b",
            "episode_id": EPISODE_ID,
            "domain": "chrome",
            "task_id": "030eeff7-b492-4218-b312-701ec99ee0cc",
            "sibling_href": f"7b/{slug}/episode.html",
            "run_dir": str(tmp_path),
          },
          {
            "model": "7b",
            "episode_id": EPISODE_ID,
            "domain": "chrome",
            "task_id": "030eeff7-b492-4218-b312-701ec99ee0cc",
            "sibling_href": f"a3b/{slug}/episode.html",
            "run_dir": str(tmp_path),
          },
        ],
      }
    ),
    encoding="utf-8",
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip, "7b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )

  a3b_html = (out / "a3b" / slug / "episode.html").read_text(encoding="utf-8")
  b7_html = (out / "7b" / slug / "episode.html").read_text(encoding="utf-8")

  a3b_hrefs = re.findall(r'href="([^"]+)"', a3b_html)
  b7_hrefs = re.findall(r'href="([^"]+)"', b7_html)

  sibling_a3b = f"../../7b/{slug}/episode.html"
  sibling_b7 = f"../../a3b/{slug}/episode.html"
  assert sibling_a3b in a3b_hrefs
  assert sibling_b7 in b7_hrefs
  assert sibling_a3b in a3b_hrefs  # next episode after a3b in paired order

  for href in a3b_hrefs + b7_hrefs:
    if href.startswith("../../") and href.endswith("/episode.html"):
      target = out / Path(*href.removeprefix("../../").split("/"))
      assert target.exists(), href


def _write_gold_run(root: Path, task_id: str) -> Path:
  """Minimal OSWorld-Human guided replay dir (goldTrajectories layout)."""
  PIL = pytest.importorskip("PIL.Image")
  d = root / task_id
  (d / "screenshots").mkdir(parents=True)
  (d / "manifest.json").write_text(
    json.dumps(
      {
        "task_id": task_id,
        "success": True,
        "score": 1.0,
        "instruction": 'Do "the thing" from <config>',
        "guided_by": "osworld-human",
      }
    ),
    encoding="utf-8",
  )
  rec = {
    "task_id": task_id,
    "step": 0,
    "human_step": "`CLICK` the settings button",
    "verb": "CLICK",
    "coords": [12, 34],
    "grounded_desc": "the settings button",
    "ground_raw": "(12,34)",
    "action": {"type": "click", "command": "pyautogui.click(12, 34)"},
  }
  (d / "trace.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
  img = PIL.new("RGB", (32, 20), "white")
  img.save(d / "screenshots" / "step00_before.png")
  img.save(d / "screenshots" / "final.png")
  return d


def test_select_paired_all_episodes_with_human(sample_zip: Path, tmp_path: Path):
  gold_root = tmp_path / "gold"
  _write_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  episodes, groups = select_paired_all_episodes(
    {"a3b": sample_zip, "7b": sample_zip}, gold_root=gold_root
  )
  assert len(groups) == 1
  assert {ep["model"] for ep in episodes} == {"a3b", "7b", "human"}
  assert set(groups[0]["models"]) == {"a3b", "7b", "human"}

  a3b = next(ep for ep in episodes if ep["model"] == "a3b")
  assert a3b["success"] is False  # result.txt in the zip is "0"
  # Falls back to the gold manifest (raw, unescaped at the data level).
  assert a3b["instruction"] == 'Do "the thing" from <config>'
  assert {s["model"] for s in a3b["siblings"]} == {"7b", "human"}

  human = next(ep for ep in episodes if ep["model"] == "human")
  assert human["gold_dir"]
  assert human["success"] is True
  assert human["episode_id"] == EPISODE_ID


def test_build_review_packet_with_human(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  gold_root = tmp_path / "gold"
  _write_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  episodes, groups = select_paired_all_episodes(
    {"a3b": sample_zip, "7b": sample_zip}, gold_root=gold_root
  )
  manifest_path = tmp_path / "manifest.json"
  groups[0]["in_label_batch"] = True
  write_manifest(
    manifest_path,
    episodes,
    packet_id="human_test",
    task_groups=groups,
    selection_mode="paired-all",
    label_batch=[groups[0]["task_id"]],
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip, "7b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )

  human_dir = out / "human" / EPISODE_SLUG
  human_html = (human_dir / "episode.html").read_text(encoding="utf-8")
  assert "CLICK" in human_html and "settings button" in human_html
  assert (human_dir / "step_1_before.jpg").exists()
  assert (human_dir / "step_2_final.jpg").exists()
  assert (human_dir / "human_steps.json").exists()

  index = (out / "index.html").read_text(encoding="utf-8")
  assert f"human/{EPISODE_SLUG}/episode.html" in index

  a3b_html = (out / "a3b" / EPISODE_SLUG / "episode.html").read_text(encoding="utf-8")
  assert f"../../human/{EPISODE_SLUG}/episode.html" in a3b_html

  # Quotes/angle brackets in instructions must be escaped, not break the markup.
  assert "<config>" not in index and "<config>" not in human_html
  assert not re.search(r'data-search="[^"]*"[^\s>]', index), "attribute broken by raw quote"

  # Label-batch marking surfaces as a filterable chip + row attribute.
  assert 'data-batch="1"' in index
  assert "label batch (1)" in index

  # Refresh re-renders human episodes from human_steps.json without the gold dir.
  refresh_review_packet_html(out, template_dir=TEMPLATE_DIR)
  refreshed = (human_dir / "episode.html").read_text(encoding="utf-8")
  assert "settings button" in refreshed


def _write_incomplete_gold_run(root: Path, task_id: str) -> Path:
  """A replay killed before it wrote a manifest/trace: log + screenshots only."""
  d = root / task_id
  (d / "screenshots").mkdir(parents=True)
  (d / "replay.log").write_text(
    "\n".join(f"line {i}" for i in range(200)) + "\nTIMEOUT after 1200s\n", encoding="utf-8"
  )
  return d


def test_human_screenshot_gets_grounded_crosshair(tmp_path: Path):
  PIL = pytest.importorskip("PIL.Image")
  gold_root = tmp_path / "gold"
  gold_dir = _write_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  episode_dir = tmp_path / "ep"
  assets = build_human_episode_assets(gold_dir, episode_dir, episode_id=EPISODE_ID)

  assert assets["replay_status"] == "gold"
  assert assets["steps"][0].coords == [12, 34]
  # The source screenshot is uniformly white; the marker must add red pixels.
  img = PIL.open(episode_dir / "step_1_before.jpg").convert("RGB")
  reds = [px for px in img.getdata() if px[0] > 150 and px[1] < 120 and px[2] < 120]
  assert reds, "no crosshair drawn on the grounded pixel"
  # The unmarked final screenshot stays clean.
  final = PIL.open(episode_dir / "step_2_final.jpg").convert("RGB")
  assert not [px for px in final.getdata() if px[0] > 150 and px[1] < 120 and px[2] < 120]


def test_incomplete_replay_builds_stub_with_log_tail(tmp_path: Path):
  gold_root = tmp_path / "gold"
  gold_dir = _write_incomplete_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  episode_dir = tmp_path / "ep"
  assets = build_human_stub_assets(gold_dir, episode_dir, episode_id=EPISODE_ID)

  assert assets["replay_status"] == "incomplete"
  assert assets["steps"] == []
  assert "TIMEOUT after 1200s" in assets["log_tail"]
  assert len(assets["log_tail"].splitlines()) == 40  # tail, not the whole log
  assert (episode_dir / "human_steps.json").exists()


def test_paired_all_covers_incomplete_and_gold_only_replays(sample_zip: Path, tmp_path: Path):
  """The packet must span the whole sweep: replays with no trace, and replays
  whose task never appears in the HF zips."""
  gold_root = tmp_path / "gold"
  _write_incomplete_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  _write_gold_run(gold_root, "aaaaaaaa-0000-0000-0000-000000000000")

  episodes, groups = select_paired_all_episodes(
    {"a3b": sample_zip, "7b": sample_zip},
    gold_root=gold_root,
    task_domains={"aaaaaaaa-0000-0000-0000-000000000000": "gimp"},
  )
  by_task = {g["task_id"]: g for g in groups}
  assert len(groups) == 2

  zip_task = by_task["030eeff7-b492-4218-b312-701ec99ee0cc"]
  assert zip_task["replay_status"] == "incomplete"
  assert set(zip_task["models"]) == {"a3b", "7b", "human"}

  gold_only = by_task["aaaaaaaa-0000-0000-0000-000000000000"]
  assert gold_only["replay_status"] == "gold"
  assert set(gold_only["models"]) == {"human"}
  assert gold_only["domain"] == "gimp"
  assert set(gold_only["missing_models"]) == {"a3b", "7b"}

  human_eps = [ep for ep in episodes if ep["model"] == "human"]
  assert len(human_eps) == 2
  assert {ep["replay_status"] for ep in human_eps} == {"incomplete", "gold"}


def test_build_review_packet_renders_incomplete_replay(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  gold_root = tmp_path / "gold"
  _write_incomplete_gold_run(gold_root, "030eeff7-b492-4218-b312-701ec99ee0cc")
  episodes, groups = select_paired_all_episodes(
    {"a3b": sample_zip, "7b": sample_zip}, gold_root=gold_root
  )
  manifest_path = tmp_path / "manifest.json"
  write_manifest(
    manifest_path, episodes, packet_id="incomplete_test", task_groups=groups,
    selection_mode="paired-all",
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip, "7b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )

  human_html = (out / "human" / EPISODE_SLUG / "episode.html").read_text(encoding="utf-8")
  assert "Replay audit" in human_html
  assert "TIMEOUT after 1200s" in human_html
  assert "ui-drift" in human_html and "grounding-miss" in human_html
  assert "produced no trace" in human_html
  # Judge panel is meaningless for a replay and must not render there.
  assert "Judge / pipeline attribution" not in human_html

  a3b_html = (out / "a3b" / EPISODE_SLUG / "episode.html").read_text(encoding="utf-8")
  assert "Judge / pipeline attribution" in a3b_html
  assert "Replay audit" not in a3b_html

  index = (out / "index.html").read_text(encoding="utf-8")
  assert 'data-replay="incomplete"' in index
  assert 'data-task-id="030eeff7-b492-4218-b312-701ec99ee0cc"' in index
  assert "replay incomplete" in index


def _write_offline_judge(path: Path, mode: str) -> Path:
  row = {
    "uid": "opencua-3b/chrome/030eeff7-b492-4218-b312-701ec99ee0cc",
    "model": "opencua-3b",
    "domain": "chrome",
    "task_id": "030eeff7-b492-4218-b312-701ec99ee0cc",
    "num_steps": 17,
    "parse_ok": True,
    "classification": {
      "analysis": "offline judge analysis text",
      "category": "perception_grounding",
      "primary_failure_mode": mode,
      "failing_step": 16,
      "secondary_failure_modes": [],
      "confidence": 0.9,
    },
  }
  skipped = {**row, "model": "claude-sonnet-4.5", "uid": "claude-sonnet-4.5/chrome/x"}
  unparsed = {**row, "parse_ok": False}
  path.write_text(
    "\n".join(json.dumps(r) for r in (row, skipped, unparsed)) + "\n", encoding="utf-8"
  )
  return path


def test_offline_judges_attach_and_render(sample_zip: Path, tmp_path: Path):
  pytest.importorskip("jinja2")
  j7 = load_offline_judge(_write_offline_judge(tmp_path / "j7.jsonl", "click_region_error"))
  j32 = load_offline_judge(_write_offline_judge(tmp_path / "j32.jsonl", "reasoning_drift"))
  assert list(j7) == [("a3b", "030eeff7-b492-4218-b312-701ec99ee0cc")]

  episodes, groups = select_paired_all_episodes(
    {"a3b": sample_zip, "7b": sample_zip},
    offline_judges={"qwen7b": j7, "qwen32b": j32},
  )
  a3b = next(ep for ep in episodes if ep["model"] == "a3b")
  assert a3b["offline_judges"]["qwen7b"]["primary_failure_mode"] == "click_region_error"
  assert a3b["offline_judges"]["qwen32b"]["primary_failure_mode"] == "reasoning_drift"
  b7 = next(ep for ep in episodes if ep["model"] == "7b")
  assert b7["offline_judges"] == {}
  assert groups[0]["judges_disagree"] is True
  assert groups[0]["models"]["a3b"]["offline"] == {
    "qwen7b": "click_region_error",
    "qwen32b": "reasoning_drift",
  }

  manifest_path = tmp_path / "manifest.json"
  write_manifest(
    manifest_path, episodes, packet_id="oj_test", task_groups=groups,
    selection_mode="paired-all",
  )
  out = build_review_packet(
    manifest_path,
    zip_paths={"a3b": sample_zip, "7b": sample_zip},
    output_dir=tmp_path / "packet",
    template_dir=TEMPLATE_DIR,
  )
  a3b_html = (out / "a3b" / EPISODE_SLUG / "episode.html").read_text(encoding="utf-8")
  assert "Offline whole-trajectory judges" in a3b_html
  assert "click_region_error" in a3b_html and "reasoning_drift" in a3b_html
  assert "offline judge analysis text" in a3b_html
  b7_html = (out / "7b" / EPISODE_SLUG / "episode.html").read_text(encoding="utf-8")
  assert "Offline whole-trajectory judges" not in b7_html
  index = (out / "index.html").read_text(encoding="utf-8")
  assert 'data-judges-disagree="1"' in index
  assert "oj-badge" in index and "click_region_error" in index
  assert "oj-differ" in index  # the two judges disagree on this episode


def test_build_discovery_row_merges_human():
  ep = {
    "model": "a3b",
    "episode_id": "chrome/uuid",
    "task_id": "uuid",
    "provisional_primary": "Reasoning Drift",
    "secondary_modes": [],
    "t_star": 5,
    "evidence": "judge note",
    "confidence": 0.6,
  }
  human = {
    "modes_ordered": ["Click Region Error", "Reasoning Drift"],
    "reasoning": "human note",
    "confidence": 0.9,
    "root_step": 3,
  }
  row = build_discovery_row(ep, human, columns=["judge_modes_ordered", "human_modes_ordered", "human_reasoning", "root_step"])
  assert row["judge_modes_ordered"] == "Reasoning Drift"
  assert row["human_modes_ordered"] == "Click Region Error;Reasoning Drift"
  assert row["human_reasoning"] == "human note"
  assert row["root_step"] == "3"
