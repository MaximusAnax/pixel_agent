#!/usr/bin/env python3
"""Serve a trace review packet with multi-annotator label save to annotations.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cua_failure_analysis.review.annotations import (  # noqa: E402
  ANNOTATIONS_FILENAME,
  REGISTERED_ANNOTATORS,
  annotations_summary,
  get_annotator_labels,
  load_annotations,
  save_annotator_labels,
  save_single_episode,
  validate_annotator_id,
)

SYNC_SCRIPT = ROOT / "scripts" / "babel" / "sync_annotations.sh"


class ReviewPacketHandler(SimpleHTTPRequestHandler):
  packet_dir: Path
  annotator_id: str
  babel_sync: bool

  def end_headers(self) -> None:
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    super().end_headers()

  def do_OPTIONS(self) -> None:  # noqa: N802
    self.send_response(204)
    self.end_headers()

  def _annotations_path(self) -> Path:
    return self.packet_dir / ANNOTATIONS_FILENAME

  def _load(self) -> dict:
    return load_annotations(self._annotations_path(), packet_dir=self.packet_dir)

  def _push_babel(self) -> None:
    if not self.babel_sync or not SYNC_SCRIPT.exists():
      return
    subprocess.run(
      [str(SYNC_SCRIPT), "push", self.packet_dir.name],
      cwd=str(ROOT),
      check=False,
    )

  def _json_response(self, code: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    self.send_response(code)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_GET(self) -> None:  # noqa: N802
    parsed = urlparse(self.path)
    if parsed.path == "/api/annotations/summary":
      data = self._load()
      self._json_response(200, {"summary": annotations_summary(data)})
      return

    if parsed.path == "/api/labels":
      qs = parse_qs(parsed.query)
      annotator = (qs.get("annotator") or [self.annotator_id])[0]
      try:
        validate_annotator_id(annotator)
      except ValueError as exc:
        self.send_error(400, str(exc))
        return
      labels = get_annotator_labels(self._load(), annotator)
      self._json_response(
        200,
        {
          "annotator": annotator,
          "labels": labels,
          "registered_annotators": list(REGISTERED_ANNOTATORS),
        },
      )
      return

    return super().do_GET()

  def do_POST(self) -> None:  # noqa: N802
    if self.path != "/api/labels":
      self.send_error(404)
      return

    length = int(self.headers.get("Content-Length", 0))
    body = self.rfile.read(length)
    try:
      payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
      self.send_error(400, "Invalid JSON")
      return

    annotator = str(payload.get("annotator") or self.annotator_id)
    try:
      validate_annotator_id(annotator)
    except ValueError as exc:
      self.send_error(400, str(exc))
      return

    path = self._annotations_path()
    packet_id = self.packet_dir.name

    if "episode_key" in payload and "entry" in payload:
      save_single_episode(
        path,
        annotator,
        str(payload["episode_key"]),
        dict(payload["entry"]),
        packet_id=packet_id,
      )
    else:
      labels = payload.get("labels")
      if not isinstance(labels, dict):
        self.send_error(400, "Expected labels object or episode_key+entry")
        return
      save_annotator_labels(path, annotator, labels, packet_id=packet_id)

    self._push_babel()
    self._json_response(200, {"ok": True, "annotator": annotator})

  def log_message(self, format: str, *args) -> None:  # noqa: A003
    print(format % args)


def pull_babel_annotations(packet_id: str) -> None:
  if not SYNC_SCRIPT.exists():
    print(f"Warning: sync script not found: {SYNC_SCRIPT}", file=sys.stderr)
    return
  subprocess.run([str(SYNC_SCRIPT), "pull", packet_id], cwd=str(ROOT), check=False)


def main() -> None:
  p = argparse.ArgumentParser(description="Serve review packet with multi-annotator label API")
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument(
    "--annotator",
    required=True,
    choices=list(REGISTERED_ANNOTATORS),
    help="Annotator namespace for saves",
  )
  p.add_argument("--port", type=int, default=8765)
  p.add_argument(
    "--babel-sync",
    action="store_true",
    help="Pull annotations from Babel on start; push after each save",
  )
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  if not (packet_dir / "index.html").exists():
    raise SystemExit(f"Packet not found: {packet_dir / 'index.html'}")

  if args.babel_sync:
    pull_babel_annotations(args.packet_id)

  handler = partial(
    ReviewPacketHandler,
    directory=str(packet_dir.resolve()),
  )
  ReviewPacketHandler.packet_dir = packet_dir
  ReviewPacketHandler.annotator_id = args.annotator
  ReviewPacketHandler.babel_sync = args.babel_sync

  server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
  print(f"Serving {packet_dir}")
  print(f"Annotator: {args.annotator}")
  print(f"Open http://127.0.0.1:{args.port}/index.html")
  print(f"Saves to {ANNOTATIONS_FILENAME} (namespace: {args.annotator})")
  if args.babel_sync:
    print("Babel sync: pull on start, push on save")
  server.serve_forever()


if __name__ == "__main__":
  main()
