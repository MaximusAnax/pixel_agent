"""Tests for serve_review_packet HTTP static file serving."""

from __future__ import annotations

import importlib.util
import threading
import time
from functools import partial
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVE_SCRIPT = ROOT / "scripts" / "serve_review_packet.py"


def _load_serve_module():
  spec = importlib.util.spec_from_file_location("serve_review_packet", SERVE_SCRIPT)
  assert spec and spec.loader
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod


def test_parse_byte_range():
  mod = _load_serve_module()
  assert mod.parse_byte_range("bytes=0-1023", 5000) == (0, 1023)
  assert mod.parse_byte_range("bytes=100-", 5000) == (100, 4999)
  assert mod.parse_byte_range("bytes=-500", 5000) == (4500, 4999)
  assert mod.parse_byte_range("bytes=9000-", 5000) is None


def test_serve_mp4_range_request(tmp_path: Path):
  mod = _load_serve_module()
  packet_dir = tmp_path / "test_packet"
  episode_dir = packet_dir / "a3b" / "chrome__test"
  episode_dir.mkdir(parents=True)
  mp4 = episode_dir / "recording.mp4"
  mp4.write_bytes(b"\x00" * 2048)
  (packet_dir / "index.html").write_text("<html></html>", encoding="utf-8")

  handler = partial(mod.ReviewPacketHandler, directory=str(packet_dir.resolve()))
  mod.ReviewPacketHandler.packet_dir = packet_dir
  mod.ReviewPacketHandler.annotator_id = "abdoul"
  mod.ReviewPacketHandler.babel_sync = False

  server = mod.ThreadingHTTPServer(("127.0.0.1", 0), handler)
  port = server.server_address[1]
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  time.sleep(0.1)

  try:
    conn = HTTPConnection("127.0.0.1", port)
    conn.request(
      "GET",
      "/a3b/chrome__test/recording.mp4",
      headers={"Range": "bytes=0-1023"},
    )
    resp = conn.getresponse()
    body = resp.read()
    assert resp.status == 206
    assert resp.getheader("Content-Range") == "bytes 0-1023/2048"
    assert resp.getheader("Accept-Ranges") == "bytes"
    assert resp.getheader("Content-Type") == "video/mp4"
    assert len(body) == 1024

    conn = HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/a3b/chrome__test/recording.mp4")
    resp = conn.getresponse()
    body = resp.read()
    assert resp.status == 200
    assert len(body) == 2048
    assert resp.getheader("Accept-Ranges") == "bytes"
  finally:
    server.shutdown()
