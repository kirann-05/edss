#!/usr/bin/env bash
# make smoke: does EDSS come up from a fresh clone, following docs/RUNBOOK.md, and work?
#
# Clones the committed repository (not the working folder, so nothing uncommitted can help) into a
# temporary folder, writes a .env with freshly generated secrets, brings the whole system up under
# its own compose project and ports, signs in, runs one brief to review, checks the audit chain,
# takes a backup and proves it restores, and takes everything down again, data included.
#
# Needs: git, Docker (OrbStack or Docker Desktop), Python 3.12 with uv. Nothing else.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
PROJECT="edss-smoke"
WEB_PORT="${SMOKE_WEB_PORT:-3410}"
DB_PORT="${SMOKE_DB_PORT:-5442}"

compose() { (cd "$WORK/edss" && docker compose -p "$PROJECT" --env-file .env --profile app "$@"); }
cleanup() {
  echo "Taking the smoke system down, its data too..."
  compose down -v >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

echo "1. A fresh clone of the committed repository"
git clone -q "$ROOT" "$WORK/edss"

echo "2. A .env with new secrets (runbook step 3)"
secret() { python3 -c "import secrets; print(secrets.token_urlsafe(24))"; }
cat > "$WORK/edss/.env" <<EOF
DATA_MODE=synthetic
EDSS_DB_PASSWORD=$(secret)
EDSS_DB_APP_PASSWORD=$(secret)
EDSS_DB_PORT=$DB_PORT
EDSS_WEB_PORT=$WEB_PORT
JWT_SECRET=$(secret)$(secret)
EDSS_SEED_PASSWORD=$(secret)
EDSS_DEMO_LOGIN=true
EOF
chmod 600 "$WORK/edss/.env"

echo "3. Everything up (runbook step 4)"
started=$(date +%s)
compose up -d --build --wait >/dev/null
echo "   up and healthy in $(( $(date +%s) - started )) s"

echo "4. Sign in, run a brief to review, check the audit chain"
(cd "$ROOT/backend" && uv run python - "$WEB_PORT" <<'PY'
import sys, time
import httpx2

web = httpx2.Client(base_url=f"http://127.0.0.1:{sys.argv[1]}", timeout=30)
assert web.get("/login").status_code == 200, "the sign-in page did not load"
assert web.post("/api/auth/demo-login", json={"email": "registrar@edss.test"}).status_code == 200
run = web.post("/api/runs", json={"request": "Placement and research brief for the Governing Council for 2025-26"}).json()
if run["status"] == "clarifying":
    run = web.post(f"/api/runs/{run['id']}/skip-questions").json()
assert web.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": []}).status_code == 200
for _ in range(150):
    run = web.get(f"/api/runs/{run['id']}").json()
    if run["status"] != "running":
        break
    time.sleep(0.2)
assert run["status"] == "awaiting_review", run
chain = web.get("/api/audit/verify").json()
assert chain["ok"], chain
status = web.get("/api/system/status").json()
print(f"   a brief reached review, the audit chain verifies over {chain['checked']} rows, data mode {status['data_mode']}")
PY
)

echo "5. A backup, restored to prove it (runbook step 6)"
(cd "$WORK/edss" && docker compose -p "$PROJECT" --env-file .env exec -T db pg_dump -U edss_owner -d edss --format=custom) > "$WORK/smoke.dump"
(cd "$WORK/edss" && docker compose -p "$PROJECT" --env-file .env exec -T db createdb -U edss_owner edss_restored)
(cd "$WORK/edss" && docker compose -p "$PROJECT" --env-file .env exec -T db pg_restore -U edss_owner -d edss_restored --exit-on-error) < "$WORK/smoke.dump"
rows=$(cd "$WORK/edss" && docker compose -p "$PROJECT" --env-file .env exec -T db psql -U edss_owner -d edss_restored -tAc "select count(*) from audit_log")
echo "   the backup restored with $rows audit rows"

echo "Smoke test passed: a fresh clone comes up, works, and backs up."
