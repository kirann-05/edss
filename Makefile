.PHONY: help dev api web test test-api test-web e2e lint typecheck check check-all types seed acceptance demo

help:
	@echo "make dev        run API (8000) and web (3000) together"
	@echo "make test       backend and frontend unit tests"
	@echo "make lint       ruff and eslint"
	@echo "make typecheck  tsc"
	@echo "make check      lint, typecheck, tests (run before every commit)"
	@echo "make e2e        browser tests: approval flow, faults, scoping, sign-in, keyboard, axe"
	@echo "make check-all  check, then e2e"
	@echo "make types      export the OpenAPI contract and regenerate frontend types"

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

# Not built yet. They fail loudly instead of pretending to succeed.
seed:
	@echo "make seed is not implemented yet (CHECKLIST C2 and F2)" && exit 1

acceptance:
	@echo "make acceptance is not implemented yet (CHECKLIST C6 and C7)" && exit 1

demo:
	@echo "make demo is not implemented yet" && exit 1
