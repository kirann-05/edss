# 1. Requirements

Source: `docs/SPEC.md` (derived from Chapter 15 of the 14-Lab Build Book) and the 12 rules in `CLAUDE.md`. Status is as built on 27 Oct 2026; the test that proves each one is in `11-traceability.md`.

## 1.1 Problem

Leadership reviews academic, research, placement and finance performance from separate department reports that arrive at different times in different formats. There is no single view of institution KPIs against targets, consolidated reports are weeks old when the Governing Council sees them, drilling from a KPI to its cause means going back to each department, and provisional or unreconciled figures get mistaken for final.

## 1.2 Users and roles

| Role | May do |
| --- | --- |
| Registrar | Authorise which data areas the agents may read, ask for briefs, review, approve, roll back, read the audit log, refresh data |
| Principal / Director | Ask for briefs, review, approve, edit, override, roll back, read the audit log |
| Dean | Ask for briefs, see institution KPIs and their own school's detail |
| Head of department (HOD) | See institution KPIs and their own department's detail only; cannot approve |
| Governing Council member | Read approved, published reports only |
| Administrator | Manage people and roles, see data health; cannot see figures or approve |

## 1.3 Functional requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-1 | A free-text request; the agent asks clarifying questions, proposes an editable plan, and nothing runs until a person locks it | Built |
| FR-2 | Access check: each data area needs a Registrar-authorised read scope before a run starts | Built |
| FR-3 | Four domain agents (Academic, Research, Placement, Finance) gather data in parallel and return typed views with data-health flags | Built |
| FR-4 | KPI synthesis from approved definitions with target and variance, computed deterministically | Built |
| FR-5 | Decision brief: KPI summary, options with risks and trade-offs for every off-target KPI, explicit assumptions, a data health section | Built |
| FR-6 | Drill-down from a KPI to department to source record (system, reference, as-of date, status) | Built |
| FR-7 | Validation gate V1 to V9, targeted repair within MAX_ATTEMPTS (3), escalation to a person on exhaustion | Built |
| FR-8 | Human gate: approve, edit, override (reason required) or send back, role-checked | Built |
| FR-9 | Governed publish: immutable versions, a current pointer, rollback with a reason | Built |
| FR-10 | Dashboard: institution KPIs with variance, domain metrics by department, drill-down evidence, the current approved report | Built |
| FR-11 | Data health: freshness, stale and missing flags per department per area | Built |
| FR-12 | Audit viewer and run trace, filterable, with chain verification | Built |
| FR-13 | Checkpoint and resume of a run that stopped | Built |
| FR-14 | PDF export of an approved version (browser print, styled for paper) | Built |
| FR-15 | Role-based access, with HOD and Dean scoping enforced by the server | Built |
| FR-16 | Ingestion with row validation, a reconciliation report and on-demand refresh | Built (a schedule is left to cron) |
| FR-17 | Real-data loading from the command line, switching the database to real mode once, and creating the first administrator | Built |
| FR-18 | Similar past briefs found for a new draft (vector search) | Built |

## 1.4 Non-functional requirements

| ID | Quality | Requirement | How it is met, measured |
| --- | --- | --- | --- |
| NFR-1 | Correctness | No number is ever written by the language model; every figure comes from the KPI engine | Reference tokens plus check V1; 94 of 94 injected faults caught (`results/`) |
| NFR-2 | Traceability | Every figure traces to a record with source system, reference, as-of date and status | Check V7; drill-down |
| NFR-3 | Honesty of figures | Provisional, forecast and unreconciled figures never shown as final; a miss never hidden by rounding | Checks V4, V6; status decided on unrounded values (placement 74.96 against 75 shows 75.0, missed) |
| NFR-4 | Privacy | Real data never leaves the machine; hosted models refused in real mode, checked against the database; no external tracing | `app/agents/llm.py` host check; tests in `tests/agents/test_llm.py` |
| NFR-5 | Accountability | Append-only, hash-chained audit log of every step's inputs and outputs | App role cannot update or delete; trigger refuses the owner; tamper test finds the changed row |
| NFR-6 | Reliability | A run survives a restart; retries are bounded; backups are proven by restore | LangGraph checkpoints in PostgreSQL; `make db-backup` restores and compares |
| NFR-7 | Security | HttpOnly SameSite session cookie, throttled sign-in, role and scope checks on every route, framing refused, input length limits | `backend/tests/api/test_authorization.py`, `backend/tests/api/test_scoping.py`, `backend/tests/test_throttle.py`, `frontend/e2e/headers.spec.ts` |
| NFR-8 | Performance | Four domain agents in parallel beat one at a time | 4.0 times faster at a simulated 700 ms per source (`results/2026-10-27/benchmark.md`) |
| NFR-9 | Usability and accessibility | Usable on a 1280 by 720 projector at 125 percent; WCAG 2.2 AA rules; keyboard only; status never by colour alone | axe scan and keyboard browser tests |
| NFR-10 | Maintainability | Typed, linted, tested; one place per rule | 98 percent backend line coverage; ruff, eslint, tsc clean |
| NFR-11 | Portability | One command to run on any Docker host | `make up`; `make smoke` from a fresh clone |
| NFR-12 | Local-first inference | Runs on a laptop without a GPU for development; production on a university GPU | Ollama (qwen3.5 4B) measured in `docs/evals` |

## 1.5 Constraints

- One developer, three weeks (1 to 22 Oct 2026), graded on a live end-to-end demo.
- Development on an Apple Silicon MacBook Air with no NVIDIA GPU.
- Real university data, official IQAC KPI definitions and targets, a GPU server and hosting are supplied by the university, not built here.
- NIRF and NAAC definitions may not be invented (rule 12): all 13 KPIs are placeholders marked `PLACEHOLDER_PENDING_IQAC`.

## 1.6 Assumptions

- Departments can export CSV files or expose read-only SQL views with a department code, metric, period, value, status and as-of date.
- Freshness equals the ingestion cadence; "real time" means as fresh as the last load, and every figure shows its as-of date.
- One API process serves one institution (decision D31).

## 1.7 Out of scope

University single sign-on, email distribution to the Governing Council, several institutions in one deployment, streaming ingestion, a mobile app, and multimodal input.
