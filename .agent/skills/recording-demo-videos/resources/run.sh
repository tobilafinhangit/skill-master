#!/usr/bin/env bash
# One-command demo recorder (template): point a local dev server at STAGING, record a
# flow, render a polished mp4 — then clean up after itself. Copy to <repo>/demo/run.sh.
#
#   bash demo/run.sh <flow> ["Optional caption"]
#
# Edit the three vars below per repo. See the recording-demo-videos skill for gotchas.
set -euo pipefail
cd "$(dirname "$0")/.."

# ── per-repo config ──────────────────────────────────────────────────────────
APP_DIR="."                       # dir to run the dev server from (e.g. "." or "congrats")
DEV_CMD="npm run dev"             # how the app starts
DEV_GREP="vite"                   # pgrep/pkill pattern for the dev process
PORT=5173                         # dev server port (Vite default 5173; Congrats uses 8080)
# ─────────────────────────────────────────────────────────────────────────────

FLOW="${1:-sample}"
CAPTION="${2:-}"
ENVTARGET="${APP_DIR%/}/.env.development.local"
STAGING="${APP_DIR%/}/.env.staging"

cleanup() {
  [ -n "${DEV_PID:-}" ] && kill "$DEV_PID" 2>/dev/null || true
  pkill -f "$DEV_GREP" 2>/dev/null || true
  [ -f "$STAGING" ] && rm -f "$ENVTARGET"   # remove staging-pointer footgun (only if we created it)
}
trap cleanup EXIT

# If a .env.staging exists, point dev at staging (Vite auto-loads .env.development.local at
# higher priority than .env/.env.local; --mode is not reliably honored). Otherwise run with
# the repo's own env — fine for public/no-auth flows.
if [ -f "$STAGING" ]; then
  cp "$STAGING" "$ENVTARGET"
  echo "▶ starting dev server (staging) from $APP_DIR on :$PORT …"
else
  echo "▶ no $STAGING — starting dev server with repo env from $APP_DIR on :$PORT …"
fi

pkill -f "$DEV_GREP" 2>/dev/null || true; sleep 1
( cd "$APP_DIR" && $DEV_CMD ) >/tmp/demo-dev.log 2>&1 &
DEV_PID=$!
for i in $(seq 1 30); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/" 2>/dev/null)" = "200" ] && break
  sleep 2
done

echo "▶ recording flow '$FLOW' …"
DEMO_FLOW="$FLOW" node demo/record.mjs

WEBM="$(ls -t demo/output/*.webm | head -1)"
echo "▶ polishing …"
bash demo/polish.sh "$WEBM" "$CAPTION"
echo "✅ done — see ${WEBM%.webm}.mp4   (open with: open ${WEBM%.webm}.mp4)"
