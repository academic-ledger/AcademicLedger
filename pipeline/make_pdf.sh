#!/usr/bin/env bash
# Generate a PDF of the talk deck from the hosted reveal.js render (web/public/talk.html).
# Faithful to what's presented (16:9, same styling), unlike a Marp export.
#
# Requires: Google Chrome installed (uses it directly — no Chromium download); npx (decktape).
# Usage:    bash pipeline/make_pdf.sh [output.pdf]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/academic-ledger-talk.pdf}"
PORT=8756

# regenerate the deck from source first, so the PDF matches the latest slides
if [ -f "$ROOT/.venv/bin/python" ]; then "$ROOT/.venv/bin/python" "$ROOT/pipeline/render_talk.py" >/dev/null; fi

# serve web/public locally for decktape to load
( cd "$ROOT/web/public" && python3 -m http.server "$PORT" >/dev/null 2>&1 ) &
SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
sleep 1

# decktape drives reveal.js one slide per page; point puppeteer at the system Chrome
export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
npx -y decktape reveal --size 1280x720 --pause 500 "http://localhost:$PORT/talk.html" "$OUT"

echo "wrote $OUT"
