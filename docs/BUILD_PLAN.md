# BUILD PLAN

21 days, one developer, Claude Code doing most of the typing. The book budgets 6 weeks for 14 labs, so this plan compresses by building vertical slices and by reinterpreting a few labs (SPEC section 9). Day 1 is 2026-10-02 or the day work actually starts. Adjust dates, keep the order.

## Day 0 (under 1 hour): environment check

Do not code until this is done.

- Python 3.12 (Miniforge or uv), Node 20+, pnpm, Docker Desktop running, Ollama installed with one small instruct model pulled, git and gh authenticated.
- Initialise the repo from this pack. Commit the docs as the first commit.
- Kiran confirms or changes D1 to D4 in docs/DECISIONS.md.
- Start the data request process in parallel (the signed Data Requirements Specification). The build never waits for it.

## Week 1: foundations and one vertical slice (Labs 1 to 6)

| Day | Work | Acceptance |
| --- | --- | --- |
| 1 | Repo scaffold, compose with Postgres and pgvector, Alembic baseline for every table in DATA_CONTRACT, Next.js skeleton, Makefile, synthetic generator and loader | `make seed` fills the DB, row counts asserted, every trap T1 to T10 is queryable |
| 2 | Lab 2: KPI engine. YAML definitions loader, restricted formula evaluator, weighted aggregation, variance, unrounded status, undefined on zero denominator | Tests green including T6, T7, T9. Every KPI result carries its input fact ids |
| 3 | Lab 5: MCP connector and ingestion. Scoped tokens, CSV and read-only SQL adapters, ingest validator, audit on every call | Stub agent reads only through the connector. A test swaps the CSV adapter for SQL with no agent change. A test fails if an agent imports a reader |
| 4 | Labs 1, 3, 6 start. LLM factory with data_mode guard, FakeLLM, clarify and plan skills, plan lock, runtime wrapper with hash-chained audit and Postgres checkpoints | A vague request yields at least 2 clarifying questions and an editable locked plan. The same skill handles two different requests with no code change |
| 5 | Lab 4 and first graph slice. Memory split, pgvector retrieval of similar past briefs, Academic node to KPI node to minimal brief | Retrieval returns correctly tagged and similar items. A run killed mid-way resumes from its last checkpoint |
| 6 | API (runs, SSE progress, KPIs, drill-down) and UI: login, dashboard with KPI cards, variance, status badges, drill-down drawer on real API data | Click a KPI, see domain metric, department, source ref |
| 7 | Buffer day. Fix, refactor, update VIVA_NOTES and PROGRESS. Run the slice end to end and record it | Cut decision 1 (see below) |

## Week 2: the full system (Labs 7 to 10, most of 12)

| Day | Work | Acceptance |
| --- | --- | --- |
| 8 | Labs 7 and 8. Full graph, four domain nodes in parallel via fan-out, join barrier, per-domain data-health flags, benchmark script | One command produces a full draft. Parallel beats sequential on wall-clock, with numbers saved |
| 9 | Options and risks node with structured output and numbers by reference. Per-KPI parallel drafting. Report compose with the format skill. Prior-options retrieval | Every off-target KPI has 2 or 3 options, each with assumptions, risks, trade-offs |
| 10 | Labs 9 and 10. Evidence records, checks V1 to V9, back-edge with bounded retry, targeted regeneration, escalation | Injected faults are detected and repaired within budget or escalated |
| 11 | Human gate with interrupt, approve, edit, override with reason, role checks, review queue UI | Nothing publishes without an authorised approval. Override is logged |
| 12 | Lab 12. Governed publish, versions, current pointer, rollback, audit viewer, PDF export | Publish v1 and v2, roll back to v1, verify the audit chain |
| 13 | Full drill-down UI, data health page, New Run page with clarify chat, plan editor and live progress | Demo path clickable end to end without a terminal |
| 14 | Integration day. One command from request to published brief. Share the draft with faculty (the book's week-3 checkpoint) | Cut decision 2. Write down faculty feedback |

## Week 3: assurance, real data, deployment (Labs 11, 13, 14)

| Day | Work | Acceptance |
| --- | --- | --- |
| 15 | Lab 11. Acceptance suite wired in as the gate. At least 8 injected faults | `make acceptance` green. Nothing reaches the human gate without a green report. Detection and repair rates recorded |
| 16 | RBAC complete including HOD scoping, authorisation tests for every route, secrets and injection pass | HOD cannot read another department's detail by any route |
| 17 | Lab 13. NIRF, NAAC and Strategic specialists in a registry. Real definitions as soon as IQAC supplies them | Specialist output uses valid definitions and produces checkable results |
| 18 | Real data swap-in through adapters, reconciliation with data owners, switch data_mode to real, local LLM only | Real-data run completes. Data health reviewed with the owners |
| 19 | Lab 14. Compose production profile, env docs, backup script, runbook for university IT, seed users | Clean-machine smoke test passes |
| 20 | Two full demo rehearsals, viva notes finalised, handover note, diagrams for the slides | Rehearsal inside 12 minutes with no terminal |
| 21 | Buffer | |

## Lab by lab: our interpretation and acceptance

| Lab | Our deliverable | Acceptance |
| --- | --- | --- |
| 1 | Clarify, plan, revise loop in the New Run flow | At least 2 clarifying questions on a vague request, coherent editable plan |
| 2 | KPI engine and typed tools | Numbers and lookups always via tools, covered by tests |
| 3 | Plan skill and format skill, both case-agnostic | Same skill works for two different requests without code change |
| 4 | Run state versus archive, tag and similarity retrieval | Correct tags returned, similar prior briefs returned |
| 5 | MCP connector | All data via connector, source swap needs no agent change |
| 6 | Runtime: budgets, gates, hash-chained audit, checkpoints | Every action logged with inputs and outputs, crash resumes |
| 7 | Full node graph with bounded back-edge | One command yields a full draft |
| 8 | Parallel domain fan-out and per-KPI options fan-out, deterministic merge by plan coverage | Parallel at least matches sequential quality at lower wall-clock |
| 9 | Evidence records and grounding | Every figure maps to an in-scope source, ungrounded content rejected |
| 10 | Validate, diagnose, repair | Faults detected and fixed within budget |
| 11 | Acceptance suite as the gate | No path to the human without green |
| 12 | Approval, metrics, versions, rollback, confidentiality | Only approved content publishes, rollback is clean |
| 13 | Framework packs as specialists | Domain-correct, checkable output |
| 14 | Deployed capstone with dashboard, audit, demo | Approved validated brief in one session |

## Cut lines (in this order, when behind)

1. SSO and scheduled refresh (already out of scope).
2. Governing Council distribution and any email.
3. PDF export polish. Keep a basic export.
4. Specialist packs reduced to configuration files over one shared implementation.
5. Per-KPI options fan-out reduced to a sequential loop.
6. Admin UI. Use a seed script for users.

Never cut: connector, KPI engine, validation gate, human gate, versioning with rollback, audit chain, drill-down, data health. Those are the system.

## Demo script (aim for 12 minutes)

1. Log in as Registrar. Data health shows a stale department and a missing research year.
2. New Run with a vague request. The agent asks clarifying questions. Edit and lock the plan.
3. Watch four domains run in parallel with live progress.
4. Dashboard: a missed KPI that displays as met when rounded but is marked missed. Open the drill-down to the source.
5. Open the brief: options, risks, trade-offs, assumptions, badges on provisional and forecast figures.
6. Toggle fault injection live. Validation catches it, repairs only the failing part, shows the diagnosis.
7. Log in as Principal. Edit one option, approve. Version 1 publishes.
8. Roll back, then show the audit chain verifying.
9. Log in as a HOD. Show scoping: only own department detail.
10. Close on the real-data run if it is ready.

## Risks

| Risk | Mitigation |
| --- | --- |
| Real data arrives late | Build on the synthetic set with the same contract, swap through adapters |
| No GPU on campus | FakeLLM fallback for the demo, small local model, narrow LLM surface keeps this survivable |
| Small model gives bad structured output | Pydantic validation with repair retry, validation gate, FakeLLM fallback |
| KPI definitions never arrive from IQAC | Placeholders clearly marked, demo shows the mechanism, say so out loud |
| LangGraph or MCP APIs differ from memory | Read current docs first, pin versions, small spikes before committing to a pattern |
| Scope too big for one person | Cut lines above, protect the never-cut list |
| Demo day network or hardware | Demo runs fully local, rehearse on the demo machine, keep a recorded run as backup |
