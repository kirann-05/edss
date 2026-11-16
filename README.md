# EDSS: Executive Decision Support System

**Agentic AI (26ECAC401) course project, KLE Technological University**
Worklet: Chapter 15, *Executive Decision Support System* (Agentic AI Worklets, 14-Lab Build Book)

> One real-time, drill-down view of institution-wide KPIs against NIRF/NAAC and strategic-plan targets, delivered as a validated decision brief with options and risks that a named leader approves before anything is published.

## Team

**Division:** B

| Name | USN |
| --- | --- |
| Kiran Patil | 01FE24BCI407 |
| Mudassir | 01FE23BCI008 |
| Sakshi Manvi | 01FE23BCI013 |
| Nazreen | 01FE23BCI026 |

## Repository layout

| Folder | Contents |
| --- | --- |
| [Assignments/](Assignments/) | All 12 assignments (Labs 1 to 12), each in its own folder with runnable code, a README and its run output |
| [Course_Project/](Course_Project/) | The project code (backend, frontend, scripts, data, docs), the [problem statement](Course_Project/Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf) and the [final report](Course_Project/Report/EDSS_Final_Report.pdf) |

## Quick links

| Item | Link |
| --- | --- |
| Assignments folder | [Assignments/](Assignments/) |
| Problem statement document | [Course_Project/Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf](Course_Project/Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf) |
| Final course project report (PDF) | [Course_Project/Report/EDSS_Final_Report.pdf](Course_Project/Report/EDSS_Final_Report.pdf) |
| Final report (Markdown, readable on GitHub) | [Course_Project/Report/EDSS_Final_Report.md](Course_Project/Report/EDSS_Final_Report.md) |
| Project documentation (technical dossier, UML, API, testing) | [Course_Project/docs/technical/](Course_Project/docs/technical/) |
| Specification, architecture, design decisions | [SPEC](Course_Project/docs/SPEC.md), [ARCHITECTURE](Course_Project/docs/ARCHITECTURE.md), [DECISIONS](Course_Project/docs/DECISIONS.md) |
| The 14 labs mapped to the code | [Course_Project/docs/LABS.md](Course_Project/docs/LABS.md) |
| Live demo script | [Course_Project/docs/DEMO.md](Course_Project/docs/DEMO.md) |

---

## Overview of the 12 assignments

Each assignment is one lab of the 14-lab build method, applied to our worklet. Each is a small, standalone Python prototype (standard library only) that prints an `ACCEPT:` line when the lab's acceptance criterion is met. The same capability is then built properly into the course project. Details are in [Assignments/README.md](Assignments/README.md).

| # | Lab | What it shows in EDSS | Folder |
| --- | --- | --- | --- |
| 1 | Agent vs Chatbot | A vague leadership request is clarified (at least two questions), planned, and revised into an editable plan | [Assignment-01](Assignments/Assignment-01_Agent_vs_Chatbot/) |
| 2 | Tool-Using Agent | Typed tools read institutional data and compute KPIs; no figure is hand-asserted | [Assignment-02](Assignments/Assignment-02_Tool_Using_Agent/) |
| 3 | Skill Creation | Reusable plan and decision-format skills with a fixed contract, run unchanged over two different cases | [Assignment-03](Assignments/Assignment-03_Skill_Creation/) |
| 4 | Memory and Retrieval | Short-term run state kept apart from a long-term store of prior briefs, retrieved by tag and similarity | [Assignment-04](Assignments/Assignment-04_Memory_and_Retrieval/) |
| 5 | MCP-Style Connector | One governed connector is the only path from agents to every data source | [Assignment-05](Assignments/Assignment-05_MCP_Style_Connector/) |
| 6 | Agent Runtime | Every action logged with inputs and outputs; a crashed run resumes from its checkpoint | [Assignment-06](Assignments/Assignment-06_Agent_Runtime/) |
| 7 | Agentic Node Graph | The full pipeline as an explicit graph, producing a validated decision-brief draft end to end | [Assignment-07](Assignments/Assignment-07_Agentic_Node_Graph/) |
| 8 | Parallel Swarm | Academic, Research, Placement and Finance agents run in parallel and merge, matching sequential quality faster | [Assignment-08](Assignments/Assignment-08_Parallel_Swarm/) |
| 9 | Deep Research (Grounding) | Every accepted output maps to a real, in-scope source; ungrounded candidates are rejected | [Assignment-09](Assignments/Assignment-09_Deep_Research_Grounding/) |
| 10 | Ops Resilience (Self-Healing) | An injected fault is detected, diagnosed and repaired within a bounded retry budget | [Assignment-10](Assignments/Assignment-10_Ops_Resilience_Self_Healing/) |
| 11 | SDLC Factory | The spec becomes an acceptance suite; a brief is eligible for review only when every check is green | [Assignment-11](Assignments/Assignment-11_SDLC_Factory/) |
| 12 | Safety and Governance | Only an authorised, approved result publishes; versions and rollback; unauthorised attempts rejected | [Assignment-12](Assignments/Assignment-12_Safety_and_Governance/) |

Labs 13 (discipline-specific specialists) and 14 (capstone) are demonstrated in [Assignments/lab_kit/labs/](Assignments/lab_kit/labs/) and realised in full by the course project.

Run all of them:

```bash
cd Assignments
python run_all.py                 # all 12 assignments plus labs 13 and 14
python -m pytest lab_kit/tests -q # 9 unit tests
```

---

## The course project

### Problem statement

University leadership (Principal/Director, Registrar, Deans, Governing Council) reviews academic, research, placement and finance performance from separate departmental reports that arrive on different schedules and in different formats.

- There is no single, current view of institution-wide KPIs against NIRF/NAAC or strategic-plan targets.
- By the time a consolidated report reaches the Governing Council, the numbers are weeks old.
- Drilling down from a KPI to the department or root cause means going back to each department.
- Provisional, forecast or unreconciled figures can be mistaken for final ones.

The worklet asks for a system that aggregates the four domains in parallel, synthesises institution-wide KPIs against targets, and produces a leadership-ready **decision brief with options and risks**, with drill-down evidence, that the executive approves before publication. (Source: [Chapter 15](Course_Project/Problem_Statement/Chapter15_EDSS_Problem_Statement.pdf).)

### Objectives

1. Consolidate the four domains from all departments into one institution-wide view, gathered in parallel through one governed connector.
2. Compute KPIs deterministically with target, variance and status, aggregating percentages from totals, never by averaging.
3. Draft options, risks, trade-offs and assumptions for every off-target KPI, without the language model ever writing a number.
4. Ground every figure in evidence (source system, reference, as-of date, status) reachable by drill-down.
5. Validate every draft with a hard gate, repair failures within a bounded budget, and escalate to a person when it is spent.
6. Govern publication: role-checked approval, versioned reports, rollback, and an append-only, hash-chained audit log.
7. Keep institutional data on the machine: local models only on real data, no external tracing.

### Approach

- **Agents draft and flag; a named human approves.** The human gate is a real stop in the graph, not a sentence in a prompt.
- **Numbers by reference.** A deterministic KPI engine computes every figure. The model writes text with tokens such as `{{kpi:placement_pct}}`, a number lint rejects any digit outside a token, and tokens become clickable evidence at render time.
- **Validation before people.** Nine checks (V1 to V9) gate every draft. A failure is diagnosed, only the failing part is repaired, at most 3 times, then escalated.
- **Built lab by lab, in vertical slices**, with tests written first for the KPI engine and every validation check, and every design trade-off recorded (decisions D1 to D34).

### Implementation

```
Request -> clarify -> editable plan -> person locks plan
        -> access check (Registrar-authorised scopes)
        -> Academic | Research | Placement | Finance agents   (parallel, read only through the MCP connector)
        -> KPI synthesis (deterministic engine: target, variance, status)
        -> option drafting per off-target KPI (parallel, LLM writes words only, guided by a specialist pack)
        -> report compose -> validate V1..V9 -> repair (max 3) -> human gate
        -> approve / edit / override / send back (Principal, Director, Registrar)
        -> versioned publish + rollback + hash-chained audit + dashboard
```

| Layer | Technology |
| --- | --- |
| Orchestration | LangGraph (parallel `Send` fan-out, checkpoints, interrupt for the human gate) |
| Connector | MCP server (Python MCP SDK) with per-run scoped tokens, every call audited |
| API | FastAPI, Pydantic 2, SQLAlchemy 2, Alembic |
| Storage | PostgreSQL 16 with pgvector (similar prior briefs), append-only audit table |
| Model | Local first: Ollama (qwen3.5 4B) in development, vLLM on a GPU in production; FakeLLM for tests and demo |
| Web app | Next.js, React, TypeScript, Tailwind, shadcn/ui, ECharts, TanStack Query, SSE for live progress |
| Tests | pytest, Vitest, Playwright with axe accessibility scans |
| Packaging | Docker Compose |

Main pages: dashboard with KPI drill-down, New Brief (clarify and plan), live run timeline, review queue and brief review, reports with version compare, rollback and print to PDF, audit viewer with chain verification, data health, and people administration. Roles are enforced on the server, including department scoping for Heads of Department.

### Results

From the latest full run of every suite (raw logs in [Course_Project/docs/technical/results/2026-10-27/](Course_Project/docs/technical/results/2026-10-27/)):

| Measure | Result |
| --- | --- |
| Automated tests | 1,392 passing (1,136 backend, 238 web, 18 browser) |
| API suite on PostgreSQL | 242 passing |
| Fault injection (8 fault types over 18 plans) | 94 of 94 caught by the intended check and repaired within the budget |
| Parallel domain agents vs one at a time | 4.0 times faster (the maximum possible with four agents) |
| Backend line coverage | 98 percent |
| Fresh clone in containers | Builds, runs a brief to review, verifies the audit chain, restores a backup |
| Local model (qwen3.5 4B) option drafts | 9 of 9 passed all nine checks |

**Limitations:** KPI definitions and NIRF/NAAC targets are placeholders until IQAC supplies official ones, real university data is not yet loaded, and single sign-on and HTTPS are not yet in place. See section 9 of the [final report](Course_Project/Report/EDSS_Final_Report.pdf).

### Run the project

```bash
cd Course_Project
make demo    # API on :8000, web app on http://127.0.0.1:3000 (synthetic data)
make check   # lint, typecheck, unit tests
make up      # whole system in containers on PostgreSQL
```

Requirements and every command: [Course_Project/README.md](Course_Project/README.md).
