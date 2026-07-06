#!/usr/bin/env python3
"""Serve a trace review packet with in-browser label save to human_labels.json."""

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReviewPacketHandler(SimpleHTTPRequestHandler):
  packet_dir: Path

  def end_headers(self) -> None:
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    super().end_headers()

  def do_OPTIONS(self) -> None:  # noqa: N802
    self.send_response(204)
    self.end_headers()

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
    labels_path = self.packet_dir / "human_labels.json"
    existing: dict = {}
    if labels_path.exists():
      existing = json.loads(labels_path.read_text(encoding="utf-8"))
    existing["labels"] = payload.get("labels", payload)
    existing["schema_version"] = 1
    existing["packet_id"] = self.packet_dir.name
    labels_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(b'{"ok":true}')

  def log_message(self, format: str, *args) -> None:  # noqa: A003
    print(format % args)


def main() -> None:
  p = argparse.ArgumentParser(description="Serve review packet with label save API")
  p.add_argument("packet_id", help="Subdir under data/review_packets/")
  p.add_argument("--port", type=int, default=8765)
  args = p.parse_args()

  packet_dir = ROOT / "data" / "review_packets" / args.packet_id
  if not (packet_dir / "index.html").exists():
    raise SystemExit(f"Packet not found: {packet_dir / 'index.html'}")

  handler = partial(
    ReviewPacketHandler,
    directory=str(packet_dir.resolve()),
  )
  # POST /api/labels reads this; partial() cannot set class attrs per request.
  ReviewPacketHandler.packet_dir = packet_dir

  server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
  print(f"Serving {packet_dir}")
  print(f"Open http://127.0.0.1:{args.port}/index.html")
  print("Save on episode pages writes to human_labels.json")
  print("Then: python scripts/export_discovery_worksheet.py --manifest ...")
  server.serve_forever()


if __name__ == "__main__":
  main()
