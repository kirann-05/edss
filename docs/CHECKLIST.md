# CHECKLIST: what we can finish from our side

Scope: everything that does not need the real dataset, IQAC definitions, the university GPU, the professor's feedback or a hosted LLM key. Built on the synthetic dataset and FakeLLM, behind the same interfaces the real parts will use later.

Legend: `[x]` done and verified, `[ ]` not started, `[~]` in progress, `[!]` blocked (reason given). Every item has an acceptance check. Do not tick an item until the check has been run and seen to pass.

Last updated: 2026-10-03, after the frontend and the browser tests.

## How the work is ordered

Vertical slices, as CLAUDE.md asks. Each slice goes from data to engine to API to UI for a thin path, then widens.

| Slice | Path | Demo step it unlocks (BUILD_PLAN demo script) |
| --- | --- | --- |
| 1 | Generator, KPI engine, auth, KPI and data health API, dashboard, drill-down drawer, data health page | 1 and 4 |
| 2 | FakeLLM clarify and plan, run lifecycle, SSE progress, New Run page | 2 and 3 |
| 3 | Brief composer, reference tokens, validation V1 to V9, gate, versions, Brief review, queue and Reports | 5, 6, 7 and 8 |
| 4 | Audit chain, RBAC with HOD scoping, Audit page, Admin page, print export | 8 and 9 |

## A. Machine and tooling

- [x] A1 Xcode license accepted. Check: `make --version` runs
- [x] A2 uv, Python 3.12, pnpm installed. Check: `uv run python --version` shows 3.12
- [x] A3 OrbStack installed. Check: `brew list --cask orbstack`
- [x] A4 OrbStack opened once and Docker daemon answering. Check: `docker info` succeeds (server 29.4.0)
- [x] A5 Browser for the E2E test. Locally the tests drive the Chrome already installed (no download), CI installs Chromium. Check: `make e2e`
- [x] A6 Ollama 0.35 installed, with `qwen3.5:4b` (3.4 GB) and `nomic-embed-text` (274 MB) pulled (decision C5). Check: `ollama list`

## B. Repo scaffold

- [x] B1 Makefile with `dev`, `test`, `lint`, `seed`, `acceptance`, `demo` targets (some stubs for now). Check: `make test` runs both suites
- [x] B2 `backend/` uv project, FastAPI app with `/api/health`, pytest and ruff configured. Check: `make test` green
- [x] B3 `frontend/` Next.js app, TypeScript, Tailwind, shadcn/ui, TanStack Query, ECharts. Check: `pnpm build` and `pnpm lint` green
- [x] B4 Frontend proxies `/api/*` to the backend, one origin for cookies and SSE. Check: browser fetch of `/api/health` returns JSON
- [x] B5 `.env.example` kept in sync, `.env` never committed. Check: `git ls-files | grep -c '^\.env$'` is 0
- [~] B6 CI workflow running backend tests, frontend lint, typecheck, unit tests and build. Check: workflow file lints locally with `act` or is run on first push (written, pinned to commit SHAs, linted with actionlint and every step run locally, but it sits in docs/ci until the GitHub token has the workflow scope, see PROGRESS.md)
- [ ] B7 `docker-compose.yml` with `db` (Postgres 16 and pgvector) and health check. Check: `docker compose up -d db` healthy. Needs A4

## C. Backend core (pure logic, tests written first)

- [x] C1 Domain schemas (Pydantic v2): DomainView, KpiResult, Option, Brief, ValidationReport, Plan, RunState. Check: schema tests, OpenAPI exports cleanly (`make types` regenerates the whole contract)
- [x] C2 Synthetic generator, seed 42, 8 departments, 3 years, traps T1 to T10. Check: one test per trap asserts the planted value and the expected handling
- [x] C3 FakeLLM and provider factory with data_mode guard (also checks the base URL host, decision D17). Check: real mode plus hosted provider refuses at start and at call time (`tests/agents/test_llm.py`, including a model built in synthetic mode that stops when the mode flips, and the rule 7 tracing guard)
- [x] C4 KPI engine: restricted AST evaluator, Decimal arithmetic, weighted aggregation, variance, unrounded status, undefined on zero denominator (decisions D14 to D16). Check: tests green including T6, T7, T9, every result lists its input fact ids
- [x] C5 Reference tokens `{{kpi:KEY}}` and `{{fact:ID}}`, renderer, digit and number-word lint (decision D21). Check: stray digit and spelled-out number both rejected
- [x] C6 Validation checks V1 to V9 as pure functions with locators. Check: each check has a passing and a failing fixture
- [x] C7 Fault injection helpers (8 faults from ARCHITECTURE section 10). Check: every injected fault is detected by the intended check
- [x] C8 Hash-chained audit log logic with verifier (decision D18 for the single writer). Check: tampering with any row breaks verification at that row
- [x] C9 RBAC matrix and HOD and Dean scoping functions. Check: table-driven tests for every role and action (RBAC matrix and department scope, tested against SPEC section 2)
- [x] C10 Clarify and plan skills on FakeLLM, case-agnostic. Check: vague request gives at least 2 questions, same skill handles two different requests, plan lock is immutable
- [x] C11 Brief composer and options drafting through FakeLLM with structured output and repair retry. Check: every off-target KPI gets 2 or 3 options with assumptions, risks, trade-offs
- [x] C12 Governance logic: approve, edit, override, publish, versions, current pointer, rollback. Check: publish v1 and v2, roll back to v1, audit rows written, unauthorised role refused

## D. API layer

- [x] D1 Cookie session auth, roles, demo login for synthetic mode only (guarded). Check: demo login refused when data_mode is real
- [~] D2 Routers per docs/ARCHITECTURE.md: runs, kpis, briefs, drilldown, audit, health, auth, admin. Check: OpenAPI lists every route (auth, system, kpis, domains, data health, runs, briefs, reports, audit and the plan catalogue are in, the admin router is not)
- [x] D3 Authorisation test for every route, including HOD scoping. Check: HOD cannot read another department's detail by any route (the route-table walk covers routes added later automatically)
- [~] D4 SSE run progress with node timings and retry attempt. Check: event stream test, browser shows live rows (stream, Last-Event-ID resume and attempt events are tested, the browser rows come with the New Run page)
- [x] D5 OpenAPI to TypeScript types generation so the UI contract cannot drift. Check: `make types` then `pnpm typecheck` green (also covers the plain-language input names)
- [~] D6 In-memory services behind the same interfaces the Postgres versions will implement. Check: swap is a one-file change per service (data store, users, runs, briefs, audit and the prior-brief archive are in memory behind the interfaces the Postgres versions will implement)

## E. Frontend (against the API above)

- [x] E1 Design tokens, shell, navigation by role, data mode badge, skip link, status badge components. Check: 1280px screenshot reviewed, axe has no serious issues (every role's navigation is tested, axe is clean on every page, see E15)
- [x] E2 Login page with role shown after sign in. Check: Playwright logs in as each seeded role (the demo buttons are used by every browser test, the password form, a wrong password, the lockout and sign-out are tested)
- [x] E3 Dashboard: KPI cards with target, variance chip, status, badges, rounded-miss notice, current report card. Check: T6 KPI shows "75.0" with Missed and "0.04 pts below"
- [x] E4 Drill-down drawer, deep-linkable: formula, inputs, per-department chart and table, fact list with badges, source refs. Check: click KPI, see domain metric, department, source ref
- [x] E5 Domain tabs with department comparison charts (bar with target line) and table toggle. Check: stale and missing departments shown explicitly, never as zero
- [x] E6 Data health page: department by domain matrix, batches, refresh. Check: T1 stale and T2 missing visible (the refresh button waits for the ingestion work in F2)
- [x] E7 New Run: clarify chat, editable plan, lock, live progress. Check: demo script step 2 and 3 clickable (chat clarifier, editable plan, revise in words, lock with demo faults, live timeline, all driven in the browser and by the approval-flow test)
- [x] E8 Review queue and Brief review: options, risks, trade-offs, assumptions, tabs for evidence, validation, data health, prior briefs, bottom action bar. Check: Approve disabled until green or escalated with acknowledgement
- [x] E9 Inline option edit with diff against the draft. Check: edit shows changed text, approver sees the diff
- [x] E10 Reports: versions, diff, rollback with reason and confirmation, print to PDF view. Check: demo script step 7 and 8
- [x] E11 Audit page: filters, chain verification banner, run trace timeline. Check: demo script step 8
- [x] E12 Admin page: users and scope grants (people and roles for the Administrator, data access for the Registrar)
- [~] E13 Every number in the UI opens its drill-down. Check: grep-style test that no bare figure is rendered outside the number component (KPI cards and chart rows open the drill-down, numbers inside the drawer do not yet)
- [~] E14 Empty, loading, error and stale states for every panel. Check: Storybook-free checklist walk-through in the browser (loading, error, empty and stale states exist on the dashboard and data health, the rest come with their pages)
- [x] E15 Accessibility: keyboard path, visible focus, AA contrast, chart table toggle, no colour-only meaning. Check: axe and manual keyboard pass (axe is clean at WCAG 2.2 AA on every page and key state, four keyboard-only tests pass, and the scan found and fixed two real problems. A person with a screen reader has not yet walked it, which axe cannot replace)
- [x] E16 Unit tests (Vitest) for number formatting that never hides a miss. Check: 74.96 against 75 never renders as equal
- [x] E17 One Playwright E2E: Principal logs in, opens draft, approves, sees published version, rolls back. Check: `pnpm e2e` green (13 browser tests: approval and rollback, fault injection, HOD scoping, sign-in and lockout, keyboard, axe)

## F. Needs Docker (do as soon as A4 is done)

- [ ] F1 SQLAlchemy models and Alembic baseline for every table in DATA_CONTRACT. Check: `alembic upgrade head` on empty DB
- [ ] F2 Loader from generator output into Postgres, row counts asserted, traps queryable. Check: `make seed`
- [ ] F3 Postgres implementations of the services from D6. Check: same API tests pass against Postgres
- [ ] F4 App DB role with no UPDATE or DELETE on `audit_log`. Check: an UPDATE from the app role fails
- [ ] F5 pgvector retrieval of similar past briefs with seeded history (decision D20). Check: similar and tag-matched items returned
- [ ] F6 `system_config.data_mode` is the source of truth for the LLM guard. Check: flipping it in the DB changes behaviour with no restart

## G. Needs a docs-first spike (APIs move fast)

- [~] G1 LangGraph: Send fan-out, interrupt and resume, Postgres checkpointer, bounded back-edge. Read current docs, pin versions, small spike before use (fan-out, interrupt and resume, the bounded back-edge and crash recovery pass on the in-memory checkpointer, the Postgres checkpointer waits for F)
- [ ] G2 MCP server with scoped tokens consumed through langchain-mcp-adapters, auth header per call. Same rule
- [x] G3 Test that fails the build if an agent module imports a database or file reader
- [ ] G4 Parallel versus sequential benchmark with simulated source latency, labelled as such (decision D19)

## H. Blocked on other people (not ours, never block the build)

- [!] H1 Real data extracts and the signed Data Requirements Specification: HOD, Registrar or IQAC
- [!] H2 Approved KPI definitions and targets from IQAC (placeholders until then, rule 12)
- [!] H3 University GPU server specs and who decides
- [!] H4 SSO answer (Google Workspace, Microsoft, LDAP). SSO is out of scope anyway
- [!] H5 Professor's preferred KPIs or brief format
- [!] H6 Lab grading format (notebook per lab or demo only), Kiran to ask
- [!] H7 Hosted dev LLM choice and key (deferred to Day 4, decision C3)

## I. Documentation we keep current as we go

- [~] I1 `docs/VIVA_NOTES.md` row for every component when built (what, why, rejected alternative, known weakness) (rows are filled for everything built so far, the pipeline pages are still to add)
- [~] I2 `PROGRESS.md` updated at the end of every session, new dependencies listed with a reason
- [ ] I3 `Makefile` commands section in CLAUDE.md filled in once the targets exist
- [ ] I4 Runbook for the university IT cell (Day 19, needs F and the compose profile)
