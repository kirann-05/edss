# Course Project: Executive Decision Support System (EDSS)

The full project: code, the problem statement document and the final report.

| What | Where |
| --- | --- |
| Problem statement (Chapter 15 of the 14-Lab Build Book, as shared at the start of the course) | [Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf](Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf) (text version: [docs/source/chapter15.md](docs/source/chapter15.md)) |
| Final course project report | [Report/EDSS_Final_Report.pdf](Report/EDSS_Final_Report.pdf) (source: [Report/EDSS_Final_Report.md](Report/EDSS_Final_Report.md)) |
| Backend (FastAPI, LangGraph, MCP connector, KPI engine, governance) | [backend/](backend/) |
| Frontend (Next.js web app) | [frontend/](frontend/) |
| Scripts (seed, ingest, acceptance, benchmark, demo) | [scripts/](scripts/) |
| Synthetic sample data with planted traps | [data/sample/](data/sample/) |
| Technical dossier (requirements, design, 13 UML diagrams, API, database, testing, results) | [docs/technical/](docs/technical/) |
| Specification, architecture, decisions, labs map, demo script, runbook | [docs/](docs/) |

## Run it

Needs Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+ with pnpm, `make`, and Docker for the database and container targets. All commands run from this folder (`Course_Project/`).

```bash
cd Course_Project
make demo        # the live demo: API on 8000, web app on http://127.0.0.1:3000
make check       # lint, typecheck, backend and web unit tests
make e2e         # browser tests
make acceptance  # inject every fault into every plan, write docs/acceptance-report.md
make benchmark   # parallel vs one-at-a-time domain agents
make up          # the whole system in containers on PostgreSQL
```

Every target is described in [CLAUDE.md](CLAUDE.md) (Commands) and [docs/RUNBOOK.md](docs/RUNBOOK.md). The step-by-step demo is [docs/DEMO.md](docs/DEMO.md), and "show me Lab N" answers are in [docs/LABS.md](docs/LABS.md).
