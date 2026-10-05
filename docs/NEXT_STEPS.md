# NEXT STEPS: the remaining work in small parts

Written 2026-10-04. The target date is 2026-10-22, so about 18 days. The graded thing is the live demo, and steps 1 to 9 of the demo script already work and are tested. So the order is: make the demo safe to run, then everything else only if there is time.

## Done

- D1 `make demo` (2026-10-04): ready in about 10 seconds including the production build, Ctrl-C stops both servers. Tested through a terminal with a real Ctrl-C.
- D5 ready-made state (2026-10-04): `make demo` starts with report version 1 approved and a placement and research draft waiting. `make demo-reset` puts it back in about 2 seconds without stopping. `DEMO_STATE=0 make demo` starts empty. 8 API tests.
- D2 `docs/DEMO.md` (2026-10-04): nine steps with the exact on-screen labels, checked against the running demo, plus pre-flight, fallbacks and a last-resort path.
- D3 `make rehearse` (2026-10-04): walks DEMO.md steps 1 to 9 against a production build with the ready-made state, at 1280 by 720. The steps take 8.5 seconds, about 20 with server start. It fails if DEMO.md and the test disagree on the steps (checked by removing step 6).
- D4 projector pass (2026-10-04): the rehearsal now runs as a 1280 by 720 projector at 125 percent zoom and fails on sideways scroll or a clipped table on any of the nine screens (checked by undoing the fix). Fixed: the data health table ran off the right edge, and after approving the outcome was off screen. Screenshots in `docs/demo-screens`.
- D6 slides kit (2026-10-04): `docs/SLIDES_KIT.md` with every number tied to a test or report, and four diagrams in `docs/diagrams` (SVG and PNG, `make diagrams`). Planned pieces are drawn dashed.
- D7 viva notes pass (2026-10-04): every answer can be said out loud and carries the measured numbers, the weakest part is answered plainly (the planner on a small model), stale answers fixed, and questions added on the canned demo, the fairness of the evaluation and what the university still owes.
- L1 `make acceptance` (2026-10-04): 18 plans, 94 fault trials, all caught by the intended check and repaired, 18 of 18 clean drafts pass, and a stubborn model is stopped at 3 attempts. Writes `docs/acceptance-report.md` in about 2 seconds. Fails when a fault slips through (checked by making one undetectable).
- L2 `make benchmark` (2026-10-04): the same graph in parallel and with LangGraph's max_concurrency at 1, at four simulated delays, with the events confirming the agents overlapped or did not. About 3.9 to 4.0 times faster in parallel, nothing to win at zero delay. `docs/benchmark.md`.
- L4a and L4b MCP server (2026-10-04): `mcp` 2.3 read from the installed package (notes in PROGRESS.md), and every connector read served as a read-only tool. A client test calls each one and gets exactly what the in-memory connector gives, decimals included. Where it runs is D29, provisional.
- L4c tokens and audit (2026-10-04): a token per run carries the plan's areas plus reference data, expires on its own and is revoked at the end. Over real HTTP a read outside the run's areas is refused and audited, and no, unknown, revoked or expired tokens get a 401 before any tool runs. Every call is one audit row with a hash of what was returned.
- L4d MCP client and swap test (2026-10-04): `McpConnector` implements the same protocol over MCP (one background loop holds the session, the four agents share it). Every method answers the same both ways, and a whole graph run gives identical KPIs and an identical brief, in-process and over HTTP with a run token.
- L4e runs read through MCP (2026-10-04): with `CONNECTOR_URL` set, the API mounts the server at `/mcp` and each run opens its own session with a token for its plan's areas; `make demo` and `make rehearse` now run this way (`DEMO_DIRECT=1` to opt out). The token caught the trend calculation reading every area, now fixed. A test drives a run through the live app and checks every read is audited and the token is gone afterwards. Runs take about one second instead of 0.76.
- L3 framework specialists (2026-10-04): Strategic, NIRF and NAAC packs as YAML over one implementation, outside the agents (they read files). The Strategic pack guides every draft and is shown on the brief. NIRF and NAAC hold nothing until IQAC supplies definitions, and the loader and the app enforce that. 13 tests.
- L7 hybrid planner (2026-10-04): rules first, the model second, the person asked where they disagree, the rules if the model's answer is unusable, a clear 503 if the model is down (D30). Measured with qwen3.5:4b: 9 of 10 and 6 of 6, equal to the rule baseline, with 6 model calls instead of 16. The drafter was measured again with the framework guidance: 9 of 9 pass. 8 tests.
- L5a database (2026-10-04): `compose.yaml` runs PostgreSQL 16 with pgvector on 127.0.0.1 only, with the owner's password generated into `.env`. `make db-up` is healthy in about 3 seconds and `make db-check` reports PostgreSQL 16.15 and pgvector 0.8.7.
- L5b schema and migration (2026-10-04): the 19 data-contract tables as SQLAlchemy Core in `app/db/schema.py`, the first Alembic migration, and 7 tests on a throwaway database: every table exists, nothing is left to migrate, figures stay NUMERIC, the contract's statuses and rule 12 are database constraints, and downgrade takes it all away. `make db-migrate`, `make test-db`.
- L5c data in the database (2026-10-05): `app/db/dataset_store.py` writes the ingested dataset to PostgreSQL with its record ids and order kept, and reads back an identical `Dataset`. `make seed-db` finds all ten traps in the database; 4 tests, including the data traps by plain SQL and a refusal to replace real data. The app still reads from memory: switching it over is L5d to L5f.
- L5d people, grants and data mode in the database (2026-10-05): `EDSS_DATABASE=true` starts the app from PostgreSQL. The KPIs match memory mode exactly, a data mode flipped in the table shows at once with no restart (and the status page now reports the stored mode, not the env file), and new people, password resets and revoked grants survive a restart. Write-through design, one process assumed (D31). 6 tests.
- L5e audit log in the database (2026-10-05): the app connects as `edss_app`, which may read and add audit rows but is refused update, delete and truncate; a trigger refuses them to the owner too (migration 0004). Writers take a transaction-level advisory lock, so two engines writing 90 rows at once still give a gapless chain that verifies. `make db-migrate` sets the role's password from `.env`. 10 tests.
- L5f runs, briefs, versions and the pointer in the database (2026-10-05): the run and governance services write every change through (each record also kept whole as JSON). `make test-api-db` runs the whole API suite, 235 tests, with the shared app in PostgreSQL mode, and passes. Runs, briefs, versions and a rollback survive a restart; a run that was working when the server stopped is shown as stopped. The demo reset is refused in this mode, because the audit log can no longer be emptied.
- L5g checkpoints in the database (2026-10-05): LangGraph's Postgres checkpointer over a connection pool as the app role, its tables created by `make db-migrate`. After a restart a waiting draft can be approved and its run finishes, and a stopped run resumes without running its finished domain agents again. Both tests fail with the in-memory checkpointer, as they should.
- L5h similar briefs with pgvector (2026-10-05): in database mode prior briefs are embedded from their words (never figures) and searched by cosine distance behind an HNSW index. The embedder is the local `nomic-embed-text` through Ollama when `LLM_EMBED_MODEL` is set, refusing any non-local server, or a word-hashing stand-in otherwise. A test with the real local model finds the placement prior from "fewer graduates got jobs than we aimed for". 5 tests.
- L6a and L6b containers (2026-10-05): a backend image (Python 3.12 slim, uv, non-root, 704 MB) and a web image (Next.js standalone, non-root, 404 MB, no tests inside). `make up` brings up the database, a one-shot migrate-and-seed, the API in database mode and the web app, all healthy in about 15 seconds once built, on 127.0.0.1 only. A run through the web app in the containers reaches review with 25 audited MCP reads and the chain verifying. Next.js telemetry is now off everywhere.
- L6c backup and restore (2026-10-05): `make db-backup` dumps the database into `backups/` (owner-only, never committed), restores it at once into a throwaway database, compares every table with the live one and verifies the audit chain, in under 2 seconds. A test also shows that a row changed in a restored copy, with the trigger switched off by the owner, is caught by the chain check at that row.
- L6d runbook and clean-clone smoke test (2026-10-05): `docs/RUNBOOK.md` for the IT cell (install, configure, start and stop, backups with a cron line, restore, upgrade, what is not ready, troubleshooting). `make smoke` clones the committed repository, writes fresh secrets, brings everything up in 28 seconds under its own project, runs a brief to review, checks the chain, backs up and restores, and takes it all down. It found one real problem on its first run: a fresh clone had no `frontend/public`, now fixed. The in-place restore in the runbook was run by hand and the chain verified afterwards.
- R1 real data into the database (2026-10-05): `make ingest DIR=... ARGS=--db` adds a checked folder append-only, with new ids above every id already used. The first real load switches the database to real mode, keeps the synthetic records archived and unread, switches the synthetic personas off, and is audited. `make create-user` makes the first real administrator. The app in real mode needs EDSS_DATABASE, a matching stored mode, JWT_SECRET and a real administrator; it reads only real records and the manifest's departments, has no demo sign-in and no invented prior briefs. 9 tests on a database of their own, and the command line run by hand.
- Published reports in the archive (2026-10-05): every publish, by any path, adds the report as a prior for the briefs after it (embedded in database mode, kept across a restart); a brief is never offered as its own prior, and if the archive fails the approval stands and the failure is audited. In real mode the archive starts empty and fills only with reports published there. 4 tests.
- Real mode seen in a browser (2026-10-05): sign-in has no demo buttons, the header says "Real data, local only", the dashboard starts with no approved report and the placeholder and data-gap notes, and a run reaches review with no invented priors.
- CI staged with the database (2026-10-05): `docs/ci/ci.yml` gains a database job (PostgreSQL from compose.yaml, `make db-migrate`, `make test-db`, `make test-api-db`) and, on main, a containers job (`make smoke`). Not run yet: it switches on with L8.
- One brief end to end with the real local model (2026-10-05): `LLM_PROVIDER=ollama make demo` with qwen3.5:4b and runs read through MCP. "Where did we miss target this year, and what should we do about it?" was asked exactly scope and audience, planned as placement, and drafted, validated (all nine checks, first attempt) and waiting for review 27 seconds after it was asked, with options shaped by the Strategic plan pack.
- Hardening pass (2026-10-06): only loading real data can switch a database to real (an env setting alone used to write it, then block synthetic mode too); connection pools close when the app stops; `create-user` checks everything before asking for a password. The runbook's real-data steps were run inside the containers on a throwaway stack: the load, the first administrator through a terminal, the restart in real mode, all three audited, no synthetic persona left active. That run showed the app must be stopped before a load, which the runbook now says.
- Dependency audit (2026-10-06): `pip-audit` finds no known vulnerabilities in the backend's locked dependencies. `pnpm audit --prod` found one (`braces`, no fix published) through the `shadcn` command-line tool, which is not in the production image; `shadcn` moved to dev dependencies and the production audit is clean. The running app also stops answering if the database switches mode under it.
- `docs/LABS.md` (2026-10-06): each of the 14 labs, what the book asks, where it lives, what to show in under a minute, and the test that proves it.
- `make demo-video` (2026-10-06): records the rehearsal of steps 1 to 9 at projector size, slowed down with a six second pause on each step for the Say line, into `demo-video/edss-demo.webm` (about 75 seconds, never committed). It is the last-resort fallback in DEMO.md.

## How to work through it

- **One part per sitting, or two small ones.** Start a fresh session each time. Read only this file and `PROGRESS.md`. That keeps each session short, which is what keeps the usage low.
- **Every part ends with a check that passes and a commit.** If a part runs past an hour or touches more than about five files, stop and split it again.
- **Stop after D5 and the demo is safe.** Everything after that adds polish or lab coverage.

## Track D: the live demo (do these first)

| Part | What | Done when | Size |
| --- | --- | --- | --- |
| D1 | `make demo`: one command that builds the web app for production, starts the API and the web app with demo settings (synthetic data, demo sign-in, a visible source delay, canned drafts), waits until both answer, and prints the address | From a clean terminal it gives a working login page in under a minute, and Ctrl-C stops both | 30 min |
| D2 | `docs/DEMO.md`: the 12 minute walk-through, each step with the exact clicks, what to say, what the screen shows and the one thing that can go wrong with its fix. A pre-flight checklist (charge, offline, zoom, model off) and an "if all else fails" path | Kiran can read it once and run the demo. Docs only | 30 min |
| D3 | `make rehearse`: one browser test that walks demo steps 1 to 9 exactly as DEMO.md says | It passes in under 90 seconds, and fails if a step is removed | 45 min |
| D4 | Projector pass: walk the nine steps at 1280 by 720 and 125 percent zoom, and fix anything too small, clipped or slow to read | No clipped text or sideways scroll on the nine screens, with screenshots saved in `docs/demo-screens` | 45 min |
| D5 | Ready-made state: an option to start with one published report and one draft already waiting, so the Principal's steps never wait on a run, and `make demo-reset` | After `make demo` the review queue has a draft and Reports has version 1, and reset restores that in 10 seconds | 45 min |
| D6 | One page for the slides team: the measured facts (tests, the ten traps, the model evaluation, the audit chain, what is a placeholder) and the four diagrams as images | `docs/SLIDES_KIT.md` and `docs/diagrams/` exist and every number in them is checked against a test or report | 45 min |
| D7 | Viva notes final pass: add the numbers, the honest answer to "what is the weakest part", and the model evaluation findings | Every row and question has an answer a person can say out loud | 30 min |
| D8 | **Kiran:** two timed dress rehearsals from DEMO.md, then send me the list of anything awkward | A fix list, which becomes small parts of its own | Your time |

## Track L: lab coverage (optional, only if the labs are graded one by one)

Ask the professor today, it decides whether this track matters: *"Is each lab also submitted separately, or is only the live demo graded?"*

| Part | What | Done when | Size |
| --- | --- | --- | --- |
| L1 | `make acceptance`: run V1 to V9 over every injected fault and KPI, write the detection and repair rates to `docs/acceptance-report.md` | The report exists and the command fails if any fault goes undetected | 45 min |
| L2 | Benchmark script: parallel against sequential domain agents, with the simulated delay stated in the output | Numbers saved to `docs/benchmark.md` | 30 min |
| L3 | Framework specialists (NIRF, NAAC, strategic) as small packs over one registry, carrying the placeholder marker | A test shows each pack is used and nothing invents a definition | 45 min |
| L4a | MCP spike: read the installed SDK, serve one read tool, call it from a client, write down what was true | A passing test and four lines of notes in PROGRESS.md | 30 min |
| L4b | MCP server with every read tool, over the existing connector interface | A client test lists and calls each tool | 45 min |
| L4c | Scoped tokens and one audit row per call | A call outside its scope is refused and audited | 45 min |
| L4d | A connector client behind the same interface, and the swap test | The KPI results are identical through MCP and directly | 45 min |
| L4e | The graph reads through MCP, and the connector runs as its own service | A full run completes over MCP | 45 min |
| L5a | Compose file with Postgres and pgvector, and a connection check | `docker compose up -d db` is healthy | 30 min |
| L5b | SQLAlchemy models and the first Alembic migration for every table in the data contract | `alembic upgrade head` on an empty database | 45 min |
| L5c | Load the sample into the database and read it back | `make seed` fills the tables and finds all ten traps by query | 45 min |
| L5d | Users, scope grants and data mode in the database | Flipping data mode in the database changes behaviour with no restart | 45 min |
| L5e | Audit log in the database with one writer at a time and an app role that cannot update or delete it | An update from the app role fails | 60 min |
| L5f | Runs, briefs, versions and the current pointer in the database | The same API tests pass against Postgres | 60 min |
| L5g | LangGraph checkpointer on Postgres | A run survives a server restart | 30 min |
| L5h | Embeddings and similar-brief retrieval with pgvector | Prior briefs come back by similarity | 45 min |
| L6a | Backend and frontend images | Both build and answer | 45 min |
| L6b | Compose with the database, backend and frontend, with health checks | One command brings up the whole system | 45 min |
| L6c | Backup script and a restore test | A restored database passes the audit chain check | 30 min |
| L6d | Runbook for the IT cell and a clean-machine smoke test | The smoke test passes from a fresh clone | 45 min |
| L7 | Hybrid planner: rules first, model second, ask where they disagree | The evaluation shows the planner scores at least the rule-based baseline | 45 min |
| L8 | **Kiran:** `gh auth refresh -h github.com -s workflow`, then move `docs/ci/ci.yml` to `.github/workflows/` | CI runs on the next push | 5 min |

## Track R: real data (needs Kiran's choices first)

| Part | What | Done when | Size |
| --- | --- | --- | --- |
| R1 | Load a folder of the university's exports into PostgreSQL, append-only, and let the app start with `DATA_MODE=real` | A real-mode folder goes in, the reconciliation report is shown, the app starts in real mode with only those records, and a hosted model is refused | 90 min |

Kiran chose the recommended options on 2026-10-05: D32, D33, D34.

## A calendar that fits

| When | What |
| --- | --- |
| Oct 4 to 10 | D1 to D5, two or three parts per sitting. The demo is then safe |
| Oct 11 to 17 | D6, D7, D8, then L1 and L2 for measured numbers |
| Oct 18 to 22 | Rehearse, slides, buffer. L3 to L7 only if the professor says the labs are graded separately |

Everything that needs the university or someone else is in [PENDING.md](PENDING.md), and none of it blocks Track D.
