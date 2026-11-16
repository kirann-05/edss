# 8. Implementation

## 8.1 Status

Every module in `07-detailed-design.md` is built and tested. What remains is not code: the university's data, IQAC's official definitions and targets, a GPU server, hosting and single sign-on (`docs/PENDING.md`).

| Module | Status | Main code |
| --- | --- | --- |
| M1 Ingestion and reconciliation | Built | `backend/app/ingestion`, `scripts/ingest.py` |
| M2 KPI engine | Built | `backend/app/kpi` |
| M3 Planner | Built | `backend/app/agents/skills/plan_skill.py` |
| M4 Domain fan-out and scoped reading | Built | `backend/app/agents/graph.py`, `backend/app/mcp_connector` |
| M5 Option drafting with reference tokens | Built | `backend/app/agents/skills/options_skill.py`, `tokens.py` |
| M6 Validation gate and repair | Built | `backend/app/agents/validation`, `repair.py` |
| M7 Governance | Built | `backend/app/governance/service.py` |
| M8 Audit hash chain | Built | `backend/app/governance/audit.py`, `backend/app/db/audit_store.py` |
| M9 Data health | Built | `backend/app/services/store.py` |
| M10 Similar prior briefs | Built | `backend/app/services/archive.py`, `backend/app/db/archive_store.py` |
| Web app (all pages) | Built | `frontend/src` |
| Containers, backups, runbook | Built | `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `docs/RUNBOOK.md` |

## 8.2 Size (measured 27 Oct 2026)

| Part | Files | Lines |
| --- | --- | --- |
| Backend application (`backend/app`) | 101 | 14,178 |
| Backend tests (`backend/tests`) | 69 | 10,534 |
| Web app (`frontend/src`, excluding the generated API types) | 119 | 11,289 |
| Browser tests and rehearsal (`frontend/e2e`, `frontend/rehearse`) | 11 | |
| Command-line scripts (`scripts`) | 14 | |

Backend by package (lines): agents 3,943; services 1,887; API 1,802; database 1,476; ingestion 1,012; KPI engine 921; governance 752; synthetic data 681; MCP connector 522; core 355; domain 245; specialists 109.

## 8.3 Repository layout

```text
backend/
  app/
    agents/        graph, skills (plan, options), validation, repair, tokens, models, runtime
    api/           routes, schemas, dependencies (sessions, permissions)
    core/          settings, roles and scoping, security, throttle
    db/            schema, stores (repositories), checkpoints, backup, real-data loading
    domain/        frozen domain models and enums
    governance/    approval, versions, rollback, diff, audit chain
    ingestion/     adapters, validator, ledger, manifest, reconciliation report
    kpi/           formula grammar, engine, definitions (YAML)
    mcp_connector/ server, client, tokens, run context
    services/      runs, store, connector, users, archive, refresh, demo state
    specialists/   framework packs (Strategic, NIRF, NAAC)
    synthetic/     generator and the ten planted traps
  migrations/      Alembic 0001 to 0007
  tests/           unit, API, database, MCP, ingestion, KPI, governance, synthetic
frontend/
  src/app/         pages (App Router)
  src/components/  page parts (dashboard, brief, runs, reports, audit, health, admin)
  src/lib/         API client and queries, formatting, flags, audit helpers
  e2e/, rehearse/  Playwright browser tests and the demo rehearsal
scripts/           seed, ingest, create-user, backup, acceptance, benchmark, evaluation, smoke
docs/              specification, architecture, decisions, runbook, demo, this dossier
```

## 8.4 Coding standards

| Standard | How it is enforced |
| --- | --- |
| Python formatting and lint | `ruff format` and `ruff check` with rule sets E, F, I, UP, B and SIM (pycodestyle, pyflakes, import order, pyupgrade, bugbear, simplify), line length 100, in `make check` |
| Types | Pydantic models everywhere data crosses a boundary; frozen domain models; Python type hints throughout |
| TypeScript | `tsc --noEmit` in strict mode; types generated from the API contract (`make types`) so the client cannot drift |
| Web lint | ESLint with the Next.js rules |
| Architecture rules as tests | `tests/agents/test_architecture.py` fails if an agent imports a data store or reads YAML directly |
| Commits | Small commits, each passing `make check` first; messages say why |
| Dependencies | Pinned in `uv.lock` and `pnpm-lock.yaml`; each addition recorded in `PROGRESS.md` with its reason; `pip-audit` and `pnpm audit` clean |
| Secrets | Only in a git-ignored `.env`; never logged, never committed; real data only under the git-ignored `data/real/` |
