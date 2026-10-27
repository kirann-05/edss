# EDSS technical dossier

Everything about how EDSS is designed, built and proved, in one folder. Structured like the SDP project: requirements, principles, architecture, design patterns, UML, API, database, detailed design with algorithms and pseudocode, implementation, tools, testing, results, traceability and deployment. Every number comes from a command that was run on 27 Oct 2026, and every claim names the file in the repository that backs it.

## Contents

| # | Document | What it answers |
| --- | --- | --- |
| 1 | [Requirements](01-requirements.md) | What the system must do (18 functional, 12 non-functional), for whom, under which constraints |
| 2 | [Design principles](02-design-principles.md) | The 12 rules and where the code enforces each; the software principles applied |
| 3 | [Architecture](03-architecture.md) | Layers, components, the agent graph, the MCP connector, data flow, technology choices and why |
| 4 | [Design patterns](04-design-patterns.md) | 14 patterns, each with the class that uses it |
| 5 | [API reference](05-api.md) | All 48 operations and who may call each (generated from the code) |
| 6 | [Database](06-database.md) | 19 tables, keys, the append-only audit protection, migrations |
| 7 | [Detailed design](07-detailed-design.md) | 10 modules: candidate algorithms, the one chosen, pseudocode with inputs and outputs |
| 8 | [Implementation](08-implementation.md) | Module status, code size, repository layout, coding standards |
| 9 | [Tools](09-tools.md) | UML, testing, lint, containers, evaluation |
| 10 | [Testing and results](10-testing.md) | Test strategy, every suite with today's numbers, fault injection, coverage, model evaluation |
| 11 | [Traceability](11-traceability.md) | Requirement to module to test, and the ten planted traps |
| 12 | [Deployment](12-deployment.md) | Containers and operations |
| - | [UML diagrams](uml/) | 13 diagrams, PlantUML source and rendered PNG |
| - | [Results](results/) | Raw logs of today's run of every suite, a summary and machine-readable metrics |

## UML diagrams

| Diagram | File |
| --- | --- |
| Use cases | [01_use_cases](uml/png/01_use_cases.png) |
| Component architecture | [02_architecture](uml/png/02_architecture.png) |
| Class: domain model | [03_class_domain](uml/png/03_class_domain.png) |
| Class: agent layer and model abstraction | [04_class_agents](uml/png/04_class_agents.png) |
| Class: services, governance, storage | [05_class_services](uml/png/05_class_services.png) |
| Sequence: a brief from request to human gate | [06_sequence_brief](uml/png/06_sequence_brief.png) |
| Sequence: approval, edit and rollback | [07_sequence_approval](uml/png/07_sequence_approval.png) |
| Sequence: one governed read through MCP | [08_sequence_mcp](uml/png/08_sequence_mcp.png) |
| State: run lifecycle | [09_state_run](uml/png/09_state_run.png) |
| State: brief lifecycle | [10_state_brief](uml/png/10_state_brief.png) |
| Activity: validation gate and bounded repair | [11_activity_validate](uml/png/11_activity_validate.png) |
| Deployment | [12_deployment](uml/png/12_deployment.png) |
| Entity-relationship (database) | [13_er_database](uml/png/13_er_database.png) |

## Elsewhere in the repository

| Topic | File |
| --- | --- |
| The specification it was built from | `docs/SPEC.md`, `docs/source/chapter15.md` |
| Longer architecture narrative | `docs/ARCHITECTURE.md` |
| Every design decision with its options (D1 to D34) | `docs/DECISIONS.md` |
| Data contract, metric catalogue, the planted traps | `docs/DATA_CONTRACT.md` |
| The 14 labs, where each lives and its proof | `docs/LABS.md` |
| The live demo, the review script, viva answers | `docs/DEMO.md`, `docs/REVIEW_SCRIPT.md`, `docs/VIVA_NOTES.md` |
| Operating it | `docs/RUNBOOK.md` |
| What the university still has to supply | `docs/PENDING.md` |

## Rebuilding

`make tech-docs` re-renders the UML and regenerates the API reference (set `PLANTUML` to the PlantUML command if it is not on the path). The results are re-run with the `make` targets listed in `10-testing.md`.
