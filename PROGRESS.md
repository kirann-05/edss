# PROGRESS

Update at the end of every session. Keep it short and true.

## Lab status

| Lab | Topic | Status | Notes |
| --- | --- | --- | --- |
| 1 | Planner loop (clarify, plan, revise) | not started | Slice 2 |
| 2 | Tool-using agent, KPI engine | engine done | KPI engine, formulas, status and traps tested. Typed tool layer for the agent comes with slice 2 |
| 3 | Reusable skills | not started | |
| 4 | Memory and retrieval | not started | |
| 5 | MCP connector | not started | |
| 6 | Runtime, audit, checkpoints | not started | |
| 7 | Full node graph | not started | |
| 8 | Parallel fan-out and merge | not started | |
| 9 | Grounding and evidence | not started | |
| 10 | Validate, diagnose, repair | not started | |
| 11 | Acceptance suite as gate | not started | |
| 12 | Governance, approval, rollback | not started | |
| 13 | Framework specialists | not started | |
| 14 | Capstone and deployment | not started | |

## Decisions confirmed by Kiran

C1 to C4 in docs/DECISIONS.md (repo path, OrbStack, FakeLLM until Day 4, lab grading format to be checked). D2 to D4 still provisional. D13 to D21 are review findings with proposed defaults, awaiting Kiran.

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

## Session log

| Date | Goal | Done | Next |
| --- | --- | --- | --- |
| 2026-10-03 (later) | Slice 1: data to engine to API to dashboard | Generator with traps T1 to T10, KPI engine, definitions and targets as YAML, RBAC with department scoping, cookie auth with guarded demo sign-in, KPI list and drill-down and data health endpoints, Next.js shell, login, dashboard, drill-down drawer, department charts, data health page. 245 backend and 80 frontend tests, production build passes | Slice 2: FakeLLM clarify and plan, run lifecycle, SSE progress, New Run page |
| 2026-10-03 | Day 0: review pack, environment, repo | Pack reviewed, repo created at ~/Claude/edss with docs as first commit, decisions C1 to C4 recorded, review findings D13 to D21 logged | Kiran accepts Xcode license, then install uv, Python 3.12, pnpm, OrbStack. Confirm D13 to D21. Then Day 1 |
