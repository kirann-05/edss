# Executive Decision Support System (EDSS)

Agentic AI course project, KLE Technological University. Worklet 15: a multi-agent system that turns department data into a validated, human-approved decision brief for university leadership.

## Team

Team 15

| Name | USN | Division |
| --- | --- | --- |
| @@TEAM_MEMBER_1@@ | @@USN@@ | @@DIV@@ |
| @@TEAM_MEMBER_2@@ | @@USN@@ | @@DIV@@ |
| @@TEAM_MEMBER_3@@ | @@USN@@ | @@DIV@@ |

## Where things are

| What | Where |
| --- | --- |
| The 12 assignments | [Assignments/](Assignments/) |
| Project code | [Course-Project/](Course-Project/) |
| Problem statement (Chapter 15 of the course build book) | [Course-Project/docs/source/chapter15.md](Course-Project/docs/source/chapter15.md), original [PDF](Course-Project/docs/source/Chapter15_EDSS.pdf) |
| Project documentation (requirements, design, UML, API, testing) | [Course-Project/docs/technical/](Course-Project/docs/technical/README.md) |
| Final report | @@FINAL_REPORT_LINK@@ |
| Live demo steps | [Course-Project/docs/DEMO_QUICK.md](Course-Project/docs/DEMO_QUICK.md), full version [DEMO.md](Course-Project/docs/DEMO.md) |

## The 12 assignments

See [Assignments/README.md](Assignments/README.md) for the overview and the folder of each.

## The project

### Problem statement

Leadership reviews academic, research, placement and finance performance from separate department reports that arrive at different times in different formats. There is no single view of institution KPIs against targets, consolidated reports are weeks old when the Governing Council sees them, drilling from a KPI to its cause means going back to each department, and provisional or unreconciled figures get mistaken for final ones.

### Objectives

- One request in plain words produces a decision brief: KPIs against targets, options with risks for every miss, explicit assumptions, and a data health section.
- No number is ever written by the language model. Every figure is computed by a deterministic KPI engine and reaches the text by reference token, so it can be traced to a source record.
- Nothing is published without a named, authorised person approving it. Approved briefs are versioned, audited and reversible.
- Real university data never leaves the machine.

### Approach

Four domain agents (Academic, Research, Placement, Finance) read department data in parallel through one governed MCP connector. A KPI engine computes institution KPIs from numerators and denominators. A local language model drafts options and risks, and only words. A report node compiles the brief. A validation gate of nine checks (V1 to V9) blocks a bad draft, repairs it within a budget of three attempts, and otherwise escalates to a person with a diagnosis. A human then approves, edits, overrides or sends it back.

```
request -> clarify -> plan (person locks it) -> 4 domain agents (parallel, via MCP)
        -> KPI engine -> draft options (LLM, words only) -> compose brief
        -> validation V1..V9 -> bounded repair -> human gate -> versioned, audited report
```

The twelve non-negotiable rules the design follows are in [Course-Project/CLAUDE.md](Course-Project/CLAUDE.md), and the design with its alternatives is in [Course-Project/docs/technical/](Course-Project/docs/technical/README.md).

### Implementation

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Orchestration | LangGraph (parallel fan-out, checkpoints, human interrupt) |
| Connector | MCP server (Python MCP SDK), one scoped token per run |
| Storage | PostgreSQL 16 with pgvector, an append-only hash-chained audit log |
| Model | Local Qwen 3.5 (4B) through Ollama, behind one provider interface; a deterministic fake model for tests |
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, ECharts, TanStack Query |
| Tests | pytest, Vitest, Playwright, axe accessibility scans |
| Packaging | Docker Compose |

Code size and module status: [08-implementation.md](Course-Project/docs/technical/08-implementation.md).

### Results

Every number below comes from a command run on 27 Oct 2026 (raw logs in [docs/technical/results/](Course-Project/docs/technical/results/)).

| Measure | Result |
| --- | --- |
| Automated tests | 1,392 passing (1,136 backend, 238 web, 18 browser) |
| Backend line coverage | 98 percent |
| Fault injection (`make acceptance`) | 94 of 94 injected faults caught by the intended check and repaired |
| Parallel domain agents (`make benchmark`) | 4.0 times faster than one at a time |
| Demo rehearsal (`make rehearse`) | 9 of 9 steps |
| Fresh clone in containers (`make smoke`) | Built, used, backed up and restored |
| Real local model, one area / full brief | about 21 s / about 60 s, all nine checks passed first attempt |

Known gaps, said plainly: real university data is not loaded yet; the 13 KPI definitions and targets are placeholders until the university's IQAC supplies the official ones (we do not invent NIRF or NAAC definitions); a 4B model on a laptop is slower and its wording varies. See [Course-Project/docs/PENDING.md](Course-Project/docs/PENDING.md).

## Run it

From the project folder:

```bash
cd Course-Project
make demo                     # the live demo with canned drafts, http://127.0.0.1:3000
LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo    # with the real local model (needs Ollama running)
make check                    # lint, types, unit tests
make acceptance               # inject every fault into every plan
```

Operations, containers and the database are in [Course-Project/docs/RUNBOOK.md](Course-Project/docs/RUNBOOK.md).
