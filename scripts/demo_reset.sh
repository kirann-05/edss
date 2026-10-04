#!/usr/bin/env bash
# Back to the start of the demo without stopping it: one approved report and one draft waiting.
# Signs in as the synthetic Administrator, which only works in demo mode, and asks the API to reset.
set -euo pipefail
API="http://127.0.0.1:${DEMO_API_PORT:-8000}/api"
jar="$(mktemp)"
trap 'rm -f "$jar"' EXIT
if ! curl -sf -c "$jar" -X POST "$API/auth/demo-login" -H 'content-type: application/json' \
    -d '{"email":"admin@edss.test"}' -o /dev/null; then
  echo "Could not sign in as the demo Administrator. Is make demo running on port ${DEMO_API_PORT:-8000}?"
  exit 1
fi
curl -sf -b "$jar" -X POST "$API/demo/reset" -o /dev/null
echo "The demo is back at its start. Sign in again in the browser."
