# NEXT STEPS: the remaining work in small parts

Written 2026-10-04. The target date is 2026-10-22, so about 18 days. The graded thing is the live demo, and steps 1 to 9 of the demo script already work and are tested. So the order is: make the demo safe to run, then everything else only if there is time.

## Done

- D1 `make demo` (2026-10-04): ready in about 10 seconds including the production build, Ctrl-C stops both servers. Tested through a terminal with a real Ctrl-C.
- D5 ready-made state (2026-10-04): `make demo` starts with report version 1 approved and a placement and research draft waiting. `make demo-reset` puts it back in about 2 seconds without stopping. `DEMO_STATE=0 make demo` starts empty. 8 API tests.

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

## A calendar that fits

| When | What |
| --- | --- |
| Oct 4 to 10 | D1 to D5, two or three parts per sitting. The demo is then safe |
| Oct 11 to 17 | D6, D7, D8, then L1 and L2 for measured numbers |
| Oct 18 to 22 | Rehearse, slides, buffer. L3 to L7 only if the professor says the labs are graded separately |

Everything that needs the university or someone else is in [PENDING.md](PENDING.md), and none of it blocks Track D.
