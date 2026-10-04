#!/usr/bin/env bash
# One command for the live demo (docs/NEXT_STEPS.md D1).
#
# Builds the web app for production, starts the API and the web app with demo settings, waits until
# both answer, and prints where to go. Ctrl-C stops both. Logs go to .demo/ so the screen stays clean.
#
# Demo settings: synthetic data, the one-click role buttons on the sign-in page, canned drafts, and a
# 700 ms pause per domain agent so the parallel work can be seen (the page says it is simulated).
# Override any of them on the command line, for example:
#   LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo      the local model instead of canned drafts
#   DEMO_SKIP_BUILD=1 make demo                              reuse the last build
#   DEMO_API_PORT=8100 DEMO_WEB_PORT=3100 make demo          other ports
#   DEMO_STATE=0 make demo                                   start empty, with no report or draft ready
#   DEMO_DIRECT=1 make demo                                  agents read in process, not through MCP
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${DEMO_API_PORT:-8000}"
WEB_PORT="${DEMO_WEB_PORT:-3000}"
LOGS="$ROOT/.demo"
mkdir -p "$LOGS"

export DATA_MODE=synthetic
export NEXT_TELEMETRY_DISABLED=1  # nothing leaves this machine (rule 7)
export EDSS_DEMO_LOGIN=true
export EDSS_DEMO_STATE="$([ "${DEMO_STATE:-1}" = "0" ] && echo false || echo true)"
export LLM_PROVIDER="${LLM_PROVIDER:-fake}"
export SOURCE_LATENCY_MS="${SOURCE_LATENCY_MS:-700}"
export EDSS_API_ORIGIN="http://127.0.0.1:$API_PORT"
# agents read through the API's own MCP endpoint with a token per run (decision D29)
export CONNECTOR_URL="$([ "${DEMO_DIRECT:-0}" = "1" ] && echo "" || echo "http://127.0.0.1:$API_PORT/mcp/")"
export EDSS_DIST_DIR=".next-demo"  # its own build folder, so a dev server can keep running beside it

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop whatever is using it (lsof -iTCP:$port), or choose other"
    echo "ports: DEMO_API_PORT=8100 DEMO_WEB_PORT=3100 make demo"
    exit 1
  fi
done

if [ "${LLM_PROVIDER}" != "fake" ] && ! curl -sf "http://127.0.0.1:11434/api/version" >/dev/null; then
  echo "LLM_PROVIDER=${LLM_PROVIDER} but Ollama is not answering. Start it with: ollama serve"
  echo "Or leave LLM_PROVIDER unset for the canned drafts."
  exit 1
fi

echo "Preparing the backend..."
(cd "$ROOT/backend" && uv sync --frozen --quiet)
if [ "${DEMO_SKIP_BUILD:-0}" != "1" ]; then
  echo "Building the web app for production (about half a minute)..."
  (cd "$ROOT/frontend" && ./node_modules/.bin/next build >"$LOGS/build.log" 2>&1) || {
    echo "The build failed. The last lines of $LOGS/build.log:"; tail -20 "$LOGS/build.log"; exit 1; }
fi

pids=()
stop() {
  trap - INT TERM EXIT
  echo
  echo "Stopping the demo..."
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo "Stopped."
}
trap stop INT TERM EXIT

(cd "$ROOT/backend" && exec .venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port "$API_PORT" >"$LOGS/api.log" 2>&1) &
pids+=($!)
(cd "$ROOT/frontend" && exec ./node_modules/.bin/next start --hostname 127.0.0.1 --port "$WEB_PORT" >"$LOGS/web.log" 2>&1) &
pids+=($!)

wait_for() {
  local url=$1 name=$2
  for _ in $(seq 1 120); do
    if curl -sf -o /dev/null "$url"; then return 0; fi
    for pid in "${pids[@]}"; do
      if ! kill -0 "$pid" 2>/dev/null; then echo "The $name stopped. See $LOGS/"; exit 1; fi
    done
    sleep 0.5
  done
  echo "The $name did not answer within a minute. See $LOGS/"
  exit 1
}
wait_for "http://127.0.0.1:$API_PORT/api/health" "API"
wait_for "http://127.0.0.1:$WEB_PORT/login" "web app"

cat <<BANNER

  EDSS is ready:  http://127.0.0.1:$WEB_PORT

  Sign in with the role buttons: Registrar, Principal, Dean, Head of Department (CSE or CIVIL),
  Governing Council, Administrator. Synthetic data only.
  Drafts: ${LLM_PROVIDER}. Simulated source delay: ${SOURCE_LATENCY_MS} ms per domain agent.
  Data: $([ -n "$CONNECTOR_URL" ] && echo "agents read through the MCP connector, one token per run" || echo "agents read in process (DEMO_DIRECT=1)").
  Ready-made: $([ "$EDSS_DEMO_STATE" = "true" ] && echo "one approved report (version 1) and one draft waiting for review" || echo "nothing, it starts empty").
  Everything lives in memory. make demo-reset goes back to the start without stopping.

  Ctrl-C to stop. Logs in .demo/

BANNER
wait
