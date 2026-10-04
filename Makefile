# Next.js sends anonymous usage telemetry by default. Nothing leaves this machine (rule 7)
export NEXT_TELEMETRY_DISABLED := 1

.PHONY: help dev api web test test-api test-web e2e lint typecheck check check-all types seed ingest acceptance demo demo-reset rehearse diagrams benchmark db-up db-down up down db-check db-backup db-migrate test-db test-api-db seed-db

help:
	@echo "make dev        run API (8000) and web (3000) together"
	@echo "make test       backend and frontend unit tests"
	@echo "make lint       ruff and eslint"
	@echo "make typecheck  tsc"
	@echo "make check      lint, typecheck, tests (run before every commit)"
	@echo "make e2e        browser tests: approval flow, faults, scoping, sign-in, keyboard, axe"
	@echo "make check-all  check, then e2e"
	@echo "make demo       the live demo in one command (production build, demo settings)"
	@echo "make demo-reset back to the start of the demo without stopping it"
	@echo "make rehearse   walks docs/DEMO.md in a browser, steps 1 to 9"
	@echo "make types      export the OpenAPI contract and regenerate frontend types"
	@echo "make seed       write the synthetic sample to data/sample, read it back, check every planted trap"
	@echo "make ingest DIR=data/real/2026-10   check a folder of exports and print the reconciliation report"

dev:
	$(MAKE) -j2 api web

api:
	cd backend && uv run uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

web:
	cd frontend && pnpm dev

test: test-api test-web

test-api:
	cd backend && uv run pytest -q

test-web:
	cd frontend && pnpm test

# starts its own backend and web server on spare ports, with a fresh in-memory state
e2e:
	cd frontend && pnpm e2e

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint

typecheck:
	cd frontend && pnpm typecheck

check: lint typecheck test

check-all: check e2e

types:
	cd backend && uv run python ../scripts/export_openapi.py
	cd frontend && pnpm types

seed:
	cd backend && uv run python ../scripts/seed.py

# the same, and into PostgreSQL too (make db-up and make db-migrate first)
seed-db:
	cd backend && uv run python ../scripts/seed.py --db

ingest:
	@test -n "$(DIR)" || (echo "usage: make ingest DIR=data/real/2026-10" && exit 2)
	cd backend && uv run python ../scripts/ingest.py ../$(DIR) --mode $${MODE:-real}

# Not built yet. It fails loudly instead of pretending to succeed.
acceptance:
	cd backend && uv run python ../scripts/acceptance.py

# the live demo: production build, demo settings, one command. See scripts/demo.sh for options
demo:
	./scripts/demo.sh

# PostgreSQL with pgvector on 127.0.0.1 (compose.yaml). The password is EDSS_DB_PASSWORD in .env
db-up:
	docker compose --env-file .env up -d --wait db

db-down:
	docker compose --env-file .env stop db

# the whole system in containers: database, migrations and seed, API, web app (compose.yaml)
# a backup of the database into backups/, restored at once into a throwaway database to prove it
db-backup:
	cd backend && uv run python ../scripts/db_backup.py

up:
	docker compose --env-file .env --profile app up -d --build --wait

down:
	docker compose --env-file .env --profile app down

db-check:
	cd backend && uv run python ../scripts/db_check.py

# bring the database schema up to date (alembic, as the owner)
db-migrate:
	cd backend && uv run alembic upgrade head && uv run python ../scripts/db_roles.py

# the tests that need PostgreSQL, failing rather than skipping if it is not running
test-db:
	cd backend && EDSS_REQUIRE_DB=1 uv run pytest -q -m db

# the whole API test suite again, with the shared app keeping everything in PostgreSQL
test-api-db:
	cd backend && EDSS_REQUIRE_DB=1 EDSS_API_ON_DATABASE=1 uv run pytest -q tests/api

# parallel against one-at-a-time domain agents, written to docs/benchmark.md
benchmark:
	cd backend && uv run python ../scripts/benchmark.py

# back to the demo's ready-made start, without stopping it
demo-reset:
	./scripts/demo_reset.sh

# docs/diagrams/*.svg to PNG for the slides
diagrams:
	cd frontend && node scripts/render-diagrams.mjs

# docs/DEMO.md walked in a browser, steps 1 to 9, against its own copy of the demo
rehearse:
	cd frontend && pnpm exec playwright test -c playwright.rehearse.config.ts
