#!/usr/bin/env python3
"""Serve the failure-audit viewer with in-browser note saving.

Static-serves the build_audit_viewer.py output dir and handles
POST /api/labels {uuid, category, note} by merging into audit_labels.json
(atomic write, timestamped). Mirrors errorAnalysis/scripts/serve_review_packet.py.

Usage:
    python serve_audit.py --dir /data/.../osworld_env/gold_audit --port 8801
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class AuditHandler(SimpleHTTPRequestHandler):
    audit_dir: Path

    def do_POST(self):  # noqa: N802
        if self.path != "/api/labels":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            uuid = str(body["uuid"])
            labels_path = self.audit_dir / "audit_labels.json"
            labels = json.loads(labels_path.read_text()) if labels_path.exists() else {}
            labels[uuid] = {
                "category": str(body.get("category", ""))[:60],
                "note": str(body.get("note", ""))[:4000],
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
            }
            fd, tmp = tempfile.mkstemp(dir=self.audit_dir, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(labels, f, indent=1, sort_keys=True)
            os.replace(tmp, labels_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        except Exception as e:  # noqa: BLE001
            self.send_error(400, f"bad label payload: {e}")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--endpoint-file", type=Path, default=None,
                    help="write <host>:<port> here at startup (for tunnels)")
    args = ap.parse_args()

    handler = partial(AuditHandler, directory=str(args.dir))
    AuditHandler.audit_dir = args.dir
    if args.endpoint_file:
        args.endpoint_file.parent.mkdir(parents=True, exist_ok=True)
        args.endpoint_file.write_text(f"{socket.gethostname()}:{args.port}\n")
    print(f"serving {args.dir} on {socket.gethostname()}:{args.port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
