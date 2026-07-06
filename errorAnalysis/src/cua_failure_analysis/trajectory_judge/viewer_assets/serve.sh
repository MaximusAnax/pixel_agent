#!/bin/bash
# Serve this viewer folder over HTTP so you can open it in a browser.
# On a remote cluster: run this, then forward the port to your laptop, e.g.
#   ssh -L 8000:localhost:8000 <user>@<host>
# (VS Code's "Ports" panel forwards it automatically if you run it in the
# integrated terminal). Then open http://localhost:8000 .
# Opening index.html directly via file:// also works (data is in data.js).
cd "$(dirname "$0")"
PORT="${1:-8000}"
echo "Serving $(pwd) at http://localhost:${PORT}  (Ctrl-C to stop)"
exec python3 -m http.server "$PORT"
