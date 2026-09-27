#!/usr/bin/env bash
# Gives the local Mini App a public HTTPS address through a Cloudflare quick tunnel
# (https://<random>.trycloudflare.com), writes it to backend/.env as WEBAPP_URL,
# and keeps the tunnel open until you press Ctrl+C.
#
# Needs: cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
# Usage: scripts/dev-tunnel.sh [port]      (default port 8000, where uvicorn runs)
set -euo pipefail

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
LOG="$(mktemp)"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Install it first:"
  echo "  macOS:   brew install cloudflared"
  echo "  Windows: winget install --id Cloudflare.cloudflared"
  echo "  Linux:   see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  cp "$ROOT/backend/.env.example" "$ENV_FILE"
  echo "Created backend/.env from .env.example. Fill in BOT_TOKEN and ADMIN_TG_ID."
fi
if [ ! -d "$ROOT/frontend/dist" ]; then
  echo "frontend/dist not found, building the Mini App..."
  (cd "$ROOT/frontend" && npm install && npm run build)
fi

cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LOG" 2>&1 &
TUNNEL_PID=$!
trap 'kill $TUNNEL_PID 2>/dev/null; rm -f "$LOG"' EXIT

URL=""
for _ in $(seq 1 60); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -n1 || true)"
  [ -n "$URL" ] && break
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    cat "$LOG"
    echo "cloudflared stopped before the tunnel was ready."
    exit 1
  fi
  sleep 1
done
if [ -z "$URL" ]; then
  cat "$LOG"
  echo "Timed out waiting for the tunnel address."
  exit 1
fi

# Replace WEBAPP_URL in backend/.env (or append it).
if grep -q '^WEBAPP_URL=' "$ENV_FILE"; then
  sed -i.bak "s|^WEBAPP_URL=.*|WEBAPP_URL=$URL|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
  echo "WEBAPP_URL=$URL" >>"$ENV_FILE"
fi

cat <<MSG

  Mini App is available at: $URL
  WEBAPP_URL in backend/.env is updated.

  In other terminals (from backend/):
    uvicorn app.main:app --port $PORT
    python -m app.bot            # restart the bot so it picks up the new address

  The address changes every time this script starts. Press Ctrl+C to close the tunnel.

MSG
wait "$TUNNEL_PID"
