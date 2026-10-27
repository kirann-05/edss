# Technical dossier: plan

Everything about how EDSS is designed, built and proved, in one folder, structured the way the SDP project was (requirements, principles, architecture, patterns, UML, API, detailed design with algorithms and pseudocode, implementation, tools, testing, results). Every number comes from a command that was run, and every claim names the file that backs it.

## What goes in, and where

| # | Item | File or folder | Source of truth |
| --- | --- | --- | --- |
| 0 | Index: every item, and which review question it answers | `README.md` | this plan |
| 1 | Requirements: functional (FR), non-functional (NFR), constraints, assumptions, out of scope | `01-requirements.md` | `docs/SPEC.md`, `CLAUDE.md` rules |
| 2 | Design principles and the 12 non-negotiable rules, each with where it is enforced in code | `02-design-principles.md` | `CLAUDE.md`, the code |
| 3 | Architecture: layers, components, the agent graph, data flow, technology stack with the reason for each | `03-architecture.md` | `docs/ARCHITECTURE.md`, the code |
| 4 | Design patterns used (with the class or file for each) | `04-design-patterns.md` | the code |
| 5 | UML: use case, component, class (domain, agents, governance, connector), sequence (a brief end to end, approval, MCP read), state (run, brief), activity (validate and repair), deployment, entity-relationship | `uml/*.puml` sources, `uml/png/` rendered | the code and schema |
| 6 | API reference: every endpoint, method, role allowed, purpose | `05-api.md` (generated from the OpenAPI file) | `backend/openapi.json` |
| 7 | Database design: tables, keys, append-only rules | `06-database.md` + ER diagram | `backend/app/db/schema.py`, migrations |
| 8 | Detailed design: each module's job, the candidate algorithms considered, the one chosen and why, pseudocode with inputs and outputs | `07-detailed-design.md` | the code, `docs/DECISIONS.md` |
| 9 | Implementation: module status, size, coding standards (ruff, mypy-style typing, eslint, tsc), repository layout | `08-implementation.md` | the repo |
| 10 | Tools: UML (PlantUML), tests (pytest, Vitest, Playwright), lint, containers, CI | `09-tools.md` | the repo |
| 11 | Testing: strategy, every suite, counts, coverage, fault injection, mutation checks, the traps | `10-testing.md` | the test runs |
| 12 | Results: today's run of every suite (raw logs and a summary), acceptance report, benchmark, coverage, model evaluation | `results/` | `make` targets, `docs/evals` |
| 13 | Traceability: requirement to module to test | `11-traceability.md` | 1, 8, 11 |
| 14 | Deployment and operations | `12-deployment.md` + deployment diagram | `compose.yaml`, `docs/RUNBOOK.md` |
| 15 | Lab mapping (the 14 labs) | link to `docs/LABS.md` | existing |
| 16 | Demo, review script, viva answers | links to `docs/DEMO.md`, `docs/REVIEW_SCRIPT.md`, `docs/VIVA_NOTES.md` | existing |

## How it is built

1. Re-run every suite from `main` and keep the raw logs in `results/<date>/`, with a `summary.md` and a machine-readable `metrics.json`.
2. Write the PlantUML sources from the code (not from memory), render them with the PlantUML already installed for SDP.
3. Generate the API reference from `backend/openapi.json` so it cannot drift from the code.
4. Write the documents, each citing the file it describes.
5. Check: every file named exists, every diagram renders, every number matches a log.
