# PROGRESS

Update at the end of every session. Keep it short and true.

## Lab status

| Lab | Topic | Status | Notes |
| --- | --- | --- | --- |
| 1 | Planner loop (clarify, plan, revise) | done | Chat clarifier, editable plan, revise in words, lock. Runs on the canned model and on a real local one, measured in docs/evals |
| 2 | Tool-using agent, KPI engine | engine and typed tools done | Domain agents call typed connector functions and the KPI engine. No LLM tool-calling loop, by design (small models are weak at it) |
| 3 | Reusable skills | done | Plan skill and options skill, each with a schema, a code-side check, and prompts as data |
| 4 | Memory and retrieval | done | Run state kept apart from the archive of prior briefs. In memory, priors match on shared off-target KPIs. In database mode they are embedded (nomic-embed-text through Ollama, or a word-hashing stand-in) and found by cosine similarity with pgvector behind an HNSW index |
| 5 | MCP connector | done | Ingestion adapters (CSV, read-only SQL), validator, loader, manifest, reconciliation report. The connector as an MCP server mounted at `/mcp` (D29), a token per run for its plan's areas, one audit row per call, refusals audited, and an MCP client behind the same protocol. A whole run gives identical KPIs through MCP and directly. `make demo` reads through MCP |
| 6 | Runtime, audit, checkpoints | done | Traced nodes, hash-chained audit, crash and resume. In database mode the audit log is append-only for the app role and protected by a trigger, and checkpoints are in PostgreSQL, so a draft can be approved, or a stopped run resumed, after a restart |
| 7 | Full node graph | done | Plan lock, access check, parallel domain agents, synthesis, options, compose, validate and repair, human gate, finish |
| 8 | Parallel fan-out and merge | done | Parallelism is measured from the events and shown. `make benchmark`: with a simulated 700 ms source, the domain phase takes about 0.71 s in parallel against 2.8 s one at a time (docs/benchmark.md) |
| 9 | Grounding and evidence | done | Reference tokens, number lint, V1, evidence tab, source record dialog, scoped record lookup |
| 10 | Validate, diagnose, repair | done | Eight injectable faults, detected and repaired inside the bound or escalated, shown live in the timeline |
| 11 | Acceptance suite as gate | done | V1 to V9 gate every draft. `make acceptance` runs every fault over 18 plans: 94 of 94 caught by the intended check and repaired (docs/acceptance-report.md) |
| 12 | Governance, approval, rollback | done | Approve, edit, override, send back, versions, diff, rollback with a reason, print to PDF, audit viewer with chain check and run trace |
| 13 | Framework specialists | done | One `Specialist` implementation and a YAML pack per framework (`app/specialists/packs`). The Strategic pack guides every option draft in words and each option set records it ("Strategic plan pack" on the brief). NIRF and NAAC packs are registered but hold nothing until IQAC supplies definitions (rule 12): the loader refuses them guidance, the app refuses to start if a KPI is tagged with them, and every brief says they have no approved definitions |
| 14 | Capstone and deployment | done for synthetic data | Every page, 15 browser tests, accessibility scan, CI written (waiting for a GitHub scope). `make up` runs the whole system in containers on PostgreSQL, `make db-backup` proves each backup by restoring it, `make smoke` brings it up from a fresh clone, and docs/RUNBOOK.md is for the IT cell. Not built: real-data ingestion into the database, SSO, HTTPS in front |

## Decisions confirmed by Kiran

C1 to C7 in docs/DECISIONS.md (repo path, OrbStack, local model, lab grading format still to ask, GitHub). D13 to D24 confirmed. D2 to D4 still provisional.

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
| mcp | The connector as an MCP server and client (rule 6, Lab 5). The official Python SDK. It pulls in `opentelemetry-api` only, with no SDK or exporter, so its spans go nowhere; a test asserts no OpenTelemetry SDK is installed (rule 7) |
| psycopg[binary] | The PostgreSQL driver (psycopg 3, with its bundled libpq so nothing else is installed). PostgreSQL itself runs from `compose.yaml` |
| sqlalchemy | The database layer. Core tables in `app/db/schema.py` rather than mapped classes, because the services already have their own domain models |
| alembic | Schema migrations, generated from that metadata and read before committing (`make db-migrate`) |
| pgvector | The `vector` column type for similar-brief search (Lab 4). The extension itself is in the database image |
| langgraph-checkpoint-postgres, psycopg-pool | LangGraph's own checkpointer in PostgreSQL, over a small connection pool, so a run survives a restart (L5g). Its tables are created by the library's `setup()` in `make db-migrate` |

Frontend (`frontend/package.json`, pinned by `pnpm-lock.yaml`)

| Package | Why |
| --- | --- |
| next, react, react-dom | App framework from the stack in CLAUDE.md |
| shadcn, radix-ui, class-variance-authority, lucide-react, tw-animate-css | shadcn/ui components, accessible primitives and icons. Components are copied into `src/components/ui`, so we own them  `shadcn` itself is a dev dependency (2026-10-06): only its CSS is used, at build time, and its command-line tool pulls in `braces`, which has an advisory with no fix. It is not in the production image |
| cn | shadcn's own class-name merge helper (replaces clsx plus tailwind-merge). Repository is under the shadcn-ui organisation |
| @tanstack/react-query | Server state, caching and refetch for every page |
| echarts | Charts, as chosen in docs/UI_SPEC.md |
| @fontsource-variable/inter | Self-hosted font, so the demo works with no network |
| vitest, @vitejs/plugin-react, jsdom, @testing-library/react, @testing-library/dom, @testing-library/jest-dom, @testing-library/user-event | Unit and component tests |
| @playwright/test | The one E2E approval-flow test (docs/ARCHITECTURE.md section 10) |
| openapi-typescript | Generates API types from the backend OpenAPI contract so schema drift is a compile error (D22) |
| @axe-core/playwright | Automated accessibility scan (axe-core, WCAG 2.2 AA tags) run by the browser tests over every page and key state. Catches mechanical problems only, so it sits beside the keyboard tests and does not replace a manual pass |

## Environment (2026-10-03)

| Tool | State |
| --- | --- |
| Xcode license | Accepted |
| uv 0.12, Python 3.12.15 | Installed, backend runs on it |
| pnpm 12.8, Node 26.6 | Installed. Next.js 16.3 builds and runs on Node 26 (verified by a production build) |
| OrbStack, Docker 29.4 | Installed. Runs PostgreSQL (`make db-up`) and the containers (`make up`) |
| Ollama 0.35 | Installed. `qwen3.5:4b` (3.4 GB) and `nomic-embed-text` (274 MB) pulled (decision C5). FakeLLM stays the default |
| git, gh | OK, gh logged in as kirann-05 |
| Machine | Apple Silicon, 16 GB RAM, 185 GB free |

## Where to resume

State on 2026-10-06: everything that needs no one else is built, tested and pushed (docs/NEXT_STEPS.md, Done). 1072 backend tests (54 need the PostgreSQL from `make db-up` and skip without it, 1 needs Ollama), 224 frontend tests, 15 browser tests, the 9-step rehearsal, the API suite again in database mode (`make test-api-db`, 237), `make acceptance` (94 of 94) and `make smoke` (containers from a fresh clone). Real data can be loaded and the app run in real mode (docs/RUNBOOK.md, Real data). For "show me Lab N" see docs/LABS.md. `make demo-video` records the fallback video, and the demo is proved to run with the internet blocked (docs/DEMO.md). What remains is Kiran's (D8 rehearsals, L8 gh scope, the professor's question) and the university's (the data, IQAC's definitions, the GPU, hosting, accounts).

What is not ours is in **docs/PENDING.md**. What is still ours is split into small parts in **docs/NEXT_STEPS.md**, demo first. Do one part per session, start from those two files, and commit at the end of each part.

Facts for the next session, found by checking and not from memory:

- `mcp` installed at 2.3.0 (2026-10-04), not the 1.30 noted earlier. In 2.x `FastMCP` is gone (importing it raises with a pointer to the migration guide): the server is `mcp.server.MCPServer` and the client `mcp.Client`, which takes a URL (streamable HTTP), a stdio command, or a server object for in-process tests. A tool returning a model gets an output schema; a list or an optional arrives as `{"result": ...}`, a single model as itself. An unknown tool or a bad argument comes back as `is_error`, not an exception. Auth is a `TokenVerifier` returning an `AccessToken`, read inside a tool with `get_access_token()`
- Ollama needs `reasoning_effort: "none"` for qwen3.5, or it spends its budget thinking and returns nothing. It is sent by default (`LLM_REASONING_EFFORT`).
- GitHub Actions: pin by commit SHA. `astral-sh/setup-uv` publishes no floating major tag.
- zsh does not split unquoted variables in a shell loop. Use `bash -c` for loops over "a b" pairs.
- Run a linter and read its output after every edit to a script. Twice a replacement silently did not apply because the formatter had reworded the line first. Use an assertion on every replacement.

## Session log

| Date | Goal | Done | Next |
| --- | --- | --- | --- |
| 2026-10-06 | Hardening and demo safety | Only a real load can switch the database to real; dependency audits clean; docs/LABS.md; `make demo-video`; the rehearsal passes with outbound network denied; slides kit counts re-measured. 1072 backend tests, 237 in database mode | Kiran: D8 rehearsals (record the video then), L8 gh scope, the professor's question |
| 2026-10-04 to 05 | The demo track, the lab track and real data | D1 to D7 (`make demo`, ready-made state, `make rehearse`, projector pass, DEMO.md, slides kit, viva notes); L1 acceptance (94 of 94 faults caught), L2 benchmark (about 4 times faster in parallel), L3 framework packs, L4 MCP connector with per-run tokens, L5 PostgreSQL (schema, data, people, append-only audit role, runs and briefs, checkpoints, pgvector), L6 containers, backups proven by restore, runbook, clean-clone smoke test, L7 hybrid planner; R1 real data into the database and real mode (D32 to D34); published reports into the archive. 1063 backend tests, 237 API tests in database mode | Kiran: D8 rehearsals, L8 gh scope. University: the data, IQAC definitions, GPU, hosting, accounts |
| 2026-10-03 to 04 (long session) | Everything that did not need the university | Pages: New Run, review queue and brief review, reports with compare and rollback and print, audit with chain check and run trace, admin. Security: login lockout, audited sign-ins, sessions ended on reset. Real model: Ollama adapter, prompts, schema-constrained output, check before the gate, measured in docs/evals. Ingestion: adapters, validator, ledger, manifest, reconciliation report, `make seed`, `make ingest`, data refresh that keeps evidence ids. Tests: 15 browser tests, axe scan, 224 component tests. CI written and linted. 955 backend tests | See docs/PENDING.md |
| 2026-10-03 (frontend, part 1) | Foundations for the pipeline pages | Backend: answers carry the wording of their question, system status states the simulated source latency, the event stream header stops proxy buffering, the validation event names the failing check. Frontend: types and queries for runs, briefs, reports and audit, run progress model with 40 tests, live event hook, status badges, dialog, textarea and checkbox, stage stepper, request form, runs list. 678 backend and 161 frontend tests, typecheck and lint clean | The pages themselves, see Where to resume |
| 2026-10-03 (backend pipeline) | Slices 2 and 3 on the backend: agents, graph, governance, pipeline API | Reference tokens and number lint, validation V1 to V9, eight injectable faults with targeted repair, FakeLLM clarify, plan and options, LLM guard on provider and host, LangGraph graph with parallel domain agents, bounded repair loop, human gate and resume, hash-chained audit with a single writer, governance (approve, edit, override, send back, versions, rollback, diff), runs, briefs, reports and audit routes with SSE. 676 backend tests | Frontend for these: New Run, review queue, brief review, reports, audit |
| 2026-10-03 (later) | Slice 1: data to engine to API to dashboard | Generator with traps T1 to T10, KPI engine, definitions and targets as YAML, RBAC with department scoping, cookie auth with guarded demo sign-in, KPI list and drill-down and data health endpoints, Next.js shell, login, dashboard, drill-down drawer, department charts, data health page. 245 backend and 80 frontend tests, production build passes | Slice 2: FakeLLM clarify and plan, run lifecycle, SSE progress, New Run page |
| 2026-10-03 | Day 0: review pack, environment, repo | Pack reviewed, repo created at ~/Claude/edss with docs as first commit, decisions C1 to C4 recorded, review findings D13 to D21 logged | Kiran accepts Xcode license, then install uv, Python 3.12, pnpm, OrbStack. Confirm D13 to D21. Then Day 1 |
