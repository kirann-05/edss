# PROGRESS

Update at the end of every session. Keep it short and true.

## Lab status

| Lab | Topic | Status | Notes |
| --- | --- | --- | --- |
| 1 | Planner loop (clarify, plan, revise) | backend done | Clarify, propose, edit, revise and lock on FakeLLM, case-agnostic, plan immutable after the lock. The New Run page is still to build |
| 2 | Tool-using agent, KPI engine | engine and typed tools done | Domain agents call typed connector functions and the KPI engine. There is no LLM tool-calling loop yet, that needs a real model (Day 4) |
| 3 | Reusable skills | done on FakeLLM | Plan skill and options skill, each a function with a schema, used by the runs service and the graph |
| 4 | Memory and retrieval | partial | Seeded prior briefs with token-overlap similarity, in memory. pgvector arrives with F5 |
| 5 | MCP connector | partial | Connector protocol scoped per run, and a test that fails the build if an agent reads data directly. The real MCP server is spike G2 |
| 6 | Runtime, audit, checkpoints | partial | Traced nodes, hash-chained audit, crash and resume proven on the in-memory checkpointer. The Postgres checkpointer and the append-only DB role wait for section F |
| 7 | Full node graph | done | Plan lock, access check, parallel domain agents, synthesis, options, compose, validate and repair, human gate, finish |
| 8 | Parallel fan-out and merge | done, benchmark pending | Four domain agents run at once and the join waits for all. The honest timing script (D19) is not written |
| 9 | Grounding and evidence | backend done | Reference tokens, number lint, V1, evidence endpoint. The Evidence tab is to build |
| 10 | Validate, diagnose, repair | done | Eight injectable faults, each detected, repaired inside the bound, or escalated with a diagnosis |
| 11 | Acceptance suite as gate | partial | V1 to V9 gate every draft inside the graph. The `make acceptance` report and the measured detection rate are not built |
| 12 | Governance, approval, rollback | backend done | Approve, edit, override, send back, immutable versions, rollback, diff, refusals audited. The review and reports pages are to build |
| 13 | Framework specialists | not started | |
| 14 | Capstone and deployment | not started | |

## Decisions confirmed by Kiran

C1 to C4 in docs/DECISIONS.md (repo path, OrbStack, FakeLLM until Day 4, lab grading format to be checked). D2 to D4 still provisional. D13 to D24 are review findings and defaults I implemented, awaiting Kiran. Most are now in code, see the status table in docs/DECISIONS.md.

## Dependencies added (with reason)

Backend (`backend/pyproject.toml`, pinned by `uv.lock`)

| Package | Why |
| --- | --- |
| fastapi, uvicorn | The API server (docs/ARCHITECTURE.md) |
| pydantic-settings | Typed, validated environment config. Secrets have no defaults |
| pytest | Test runner |
| httpx2 | Starlette's test client dependency. Starlette 1.7 deprecates plain httpx for it |
| ruff | Lint and format in one tool |
| pyyaml, types-pyyaml | KPI definitions and targets are YAML data (decision D8). safe_load only |
| argon2-cffi | Password hashing. Argon2 is the current recommendation, passlib is unmaintained |
| pyjwt | Signed session tokens in an httpOnly cookie |
| langgraph | The agent graph: parallel fan-out with `Send`, `interrupt` for the human gate, checkpointing for resume, a bounded back-edge for repair (decision D2, Labs 6 to 8). It pulls in `langchain-core`, `langsmith`, `langgraph-checkpoint`, `langgraph-prebuilt` and `langgraph-sdk`. `langsmith` is the tracing client, which rule 7 forbids using, so `enforce_no_external_tracing` pins tracing off at start and a test asserts it stays off during a run |

Frontend (`frontend/package.json`, pinned by `pnpm-lock.yaml`)

| Package | Why |
| --- | --- |
| next, react, react-dom | App framework from the stack in CLAUDE.md |
| shadcn, radix-ui, class-variance-authority, lucide-react, tw-animate-css | shadcn/ui components, accessible primitives and icons. Components are copied into `src/components/ui`, so we own them |
| cn | shadcn's own class-name merge helper (replaces clsx plus tailwind-merge). Repository is under the shadcn-ui organisation |
| @tanstack/react-query | Server state, caching and refetch for every page |
| echarts | Charts, as chosen in docs/UI_SPEC.md |
| @fontsource-variable/inter | Self-hosted font, so the demo works with no network |
| vitest, @vitejs/plugin-react, jsdom, @testing-library/react, @testing-library/dom, @testing-library/jest-dom, @testing-library/user-event | Unit and component tests |
| @playwright/test | The one E2E approval-flow test (docs/ARCHITECTURE.md section 10) |
| openapi-typescript | Generates API types from the backend OpenAPI contract so schema drift is a compile error (D22) |

## Environment (2026-10-03)

| Tool | State |
| --- | --- |
| Xcode license | Accepted |
| uv 0.12, Python 3.12.15 | Installed, backend runs on it |
| pnpm 12.8, Node 26.6 | Installed. Next.js 16.3 builds and runs on Node 26 (verified by a production build) |
| OrbStack, Docker 29.4 | Installed and answering. Not used yet, Postgres arrives with section F of docs/CHECKLIST.md |
| Ollama | Not installed, deliberately. FakeLLM until Day 4 (decision C3) |
| git, gh | OK, gh logged in as kirann-05 |
| Machine | Apple Silicon, 16 GB RAM, 185 GB free |

## Where to resume (written when the usage limit was reached)

Built and tested, but not on any page yet: `frontend/src/lib/run-progress.ts` (event log to timeline rows, parallelism measured from the events), `use-run-events.ts` (live stream that reconnects and resumes), `components/runs/{stage-stepper,new-run-form,runs-list}.tsx`, status badges for runs, briefs and versions, and the dialog, textarea and checkbox primitives. Generated types and queries for runs, briefs, reports and audit are in `lib/api/`.

To write, in this order:

1. New Run: clarify panel (chat style, radio choices plus a typed answer, skip), plan editor (period, audience, options scope, KPI checklist with tri-state domains, editable step titles, revise with feedback showing what changed, revision history), progress timeline (one row per node with a bar, attempt, failing check, parallelism measured not asserted, and the simulated source latency from `/system/status` stated), the pages `/runs/new` and `/runs/[id]`, and the nav entry. Plan draft helpers go in `lib/plan-draft.ts` with tests. Send only `kpi_keys` when the selection changes, the API derives the areas from them.
2. Small backend item: `RunService.edit_plan` should store the output of `diff_plans` in the history instead of "Edited directly".
3. Review queue `/review` and brief review `/review/[id]`: figures as clickable badged segments that open the existing drill-down with the brief's period, tabs for Evidence, Validation report (every attempt), Data health and Prior briefs, bottom bar with Approve gated by `approval_state`, Edit with a dry run through `/check-edits` and a diff, Override and Send back with a required reason in a dialog.
4. Reports `/reports` (versions, diff, rollback with reason), `/reports/[version]` with a print stylesheet, and the current report card on the dashboard.
5. Audit `/audit` (filters kept in the URL, chain verification banner, expandable rows) and the run trace `/audit/runs/[id]`.
6. Then: nav entries by permission, Viewer lands on `/reports`, Vitest component tests, axe pass, Playwright E2E, Docker and Postgres (section F), MCP spike (G2), benchmark script (G4).
7. For the demo, set `SOURCE_LATENCY_MS` (for example 700) in `.env` so progress is visible, and keep it labelled as simulated (D19).

Dev servers were left running as background tasks, API on port 8000 and web on port 3000.

Questions still open for Kiran: confirm D13 to D24, ask the professor whether each lab is also submitted as a notebook (C4), confirm D2 to D4.

## Session log

| Date | Goal | Done | Next |
| --- | --- | --- | --- |
| 2026-10-03 (frontend, part 1) | Foundations for the pipeline pages | Backend: answers carry the wording of their question, system status states the simulated source latency, the event stream header stops proxy buffering, the validation event names the failing check. Frontend: types and queries for runs, briefs, reports and audit, run progress model with 40 tests, live event hook, status badges, dialog, textarea and checkbox, stage stepper, request form, runs list. 678 backend and 161 frontend tests, typecheck and lint clean | The pages themselves, see Where to resume |
| 2026-10-03 (backend pipeline) | Slices 2 and 3 on the backend: agents, graph, governance, pipeline API | Reference tokens and number lint, validation V1 to V9, eight injectable faults with targeted repair, FakeLLM clarify, plan and options, LLM guard on provider and host, LangGraph graph with parallel domain agents, bounded repair loop, human gate and resume, hash-chained audit with a single writer, governance (approve, edit, override, send back, versions, rollback, diff), runs, briefs, reports and audit routes with SSE. 676 backend tests | Frontend for these: New Run, review queue, brief review, reports, audit |
| 2026-10-03 (later) | Slice 1: data to engine to API to dashboard | Generator with traps T1 to T10, KPI engine, definitions and targets as YAML, RBAC with department scoping, cookie auth with guarded demo sign-in, KPI list and drill-down and data health endpoints, Next.js shell, login, dashboard, drill-down drawer, department charts, data health page. 245 backend and 80 frontend tests, production build passes | Slice 2: FakeLLM clarify and plan, run lifecycle, SSE progress, New Run page |
| 2026-10-03 | Day 0: review pack, environment, repo | Pack reviewed, repo created at ~/Claude/edss with docs as first commit, decisions C1 to C4 recorded, review findings D13 to D21 logged | Kiran accepts Xcode license, then install uv, Python 3.12, pnpm, OrbStack. Confirm D13 to D21. Then Day 1 |
