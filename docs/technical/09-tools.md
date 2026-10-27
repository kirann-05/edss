# 9. Tools

| Purpose | Tool | Where |
| --- | --- | --- |
| UML diagrams | PlantUML 1.2026.8 | Sources in `docs/technical/uml/*.puml`, rendered to `uml/png/` by `make tech-docs` |
| Slide diagrams | Hand-written SVG, rendered to PNG by Playwright | `docs/diagrams/`, `make diagrams` |
| Backend tests | pytest | `backend/tests`, run by `make check`, `make test-db`, `make test-api-db` |
| Coverage | coverage.py 7.16 (one-off, not a dependency) | `make coverage` |
| Web unit and component tests | Vitest, Testing Library | `frontend/src/**/*.test.ts(x)` |
| Browser tests | Playwright, with axe for accessibility (WCAG 2.2 AA rules) | `frontend/e2e`, `make e2e` |
| Demo rehearsal | Playwright walking `docs/DEMO.md` step by step at projector size | `frontend/rehearse`, `make rehearse`, `make demo-video` |
| Fault injection | Own script: every fault into every plan | `scripts/acceptance.py`, `make acceptance` |
| Benchmark | Own script: parallel against one at a time | `scripts/benchmark.py`, `make benchmark` |
| Model evaluation | Own script against a local model | `scripts/evaluate_llm.py`, reports in `docs/evals` |
| Lint and format | ruff (Python), ESLint and tsc (TypeScript) | `make check` |
| API contract | FastAPI OpenAPI export, openapi-typescript | `make types`; API reference by `scripts/build_api_doc.py` |
| Database | PostgreSQL 16, pgvector, Alembic | `compose.yaml`, `backend/migrations` |
| Containers | Docker Compose (OrbStack on the development Mac) | `make up`, `make smoke` |
| Dependency audit | pip-audit, pnpm audit | `docs/ci/ci.yml` |
| Continuous integration | GitHub Actions workflow, written and linted, waiting for a token scope to be installed | `docs/ci/ci.yml` |
| Local model | Ollama (qwen3.5 4B, nomic-embed-text) | `docs/evals` |
| Package managers | uv (Python), pnpm (web) | `uv.lock`, `pnpm-lock.yaml` |
| Version control | git, GitHub (private repository) | |
