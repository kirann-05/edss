.PHONY: help dev api web test test-api test-web e2e lint typecheck check check-all types seed ingest acceptance demo demo-reset rehearse

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

ingest:
	@test -n "$(DIR)" || (echo "usage: make ingest DIR=data/real/2026-10" && exit 2)
	cd backend && uv run python ../scripts/ingest.py ../$(DIR) --mode $${MODE:-real}

# Not built yet. It fails loudly instead of pretending to succeed.
acceptance:
	@echo "make acceptance is not implemented yet (CHECKLIST C6 and C7)" && exit 1

# the live demo: production build, demo settings, one command. See scripts/demo.sh for options
demo:
	./scripts/demo.sh

# back to the demo's ready-made start, without stopping it
demo-reset:
	./scripts/demo_reset.sh

# docs/DEMO.md walked in a browser, steps 1 to 9, against its own copy of the demo
rehearse:
	cd frontend && pnpm exec playwright test -c playwright.rehearse.config.ts
