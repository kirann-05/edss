# EDSS: Executive Decision Support System

A multi-agent decision support system for university leadership. It is a course project for Agentic AI (KLE Technological University), but it will be used by the professor on real university data and then scaled to other departments. Build it like production software, not a demo script.

- Developer: Kiran Patil (sole developer; teammates only do slides)
- Deadline: 3 weeks from 2026-10-01 (target 2026-10-22). Graded on a live end-to-end demo of a running system. The 14 labs are the build milestones.
- Source spec: Chapter 15 of the "Agentic AI Worklets, 14-Lab Build Book" (docs/source/chapter15.md, original PDF beside it)

## Read order before writing any code

1. docs/SPEC.md: what to build, rules, validation checks, definition of done
2. docs/ARCHITECTURE.md: stack, graph, state, connector, LLM layer, env vars
3. docs/DATA_CONTRACT.md: tables, metric catalogue, synthetic data with planted traps
4. docs/BUILD_PLAN.md: day-by-day plan, acceptance per lab, cut lines, demo script
5. docs/DECISIONS.md: provisional choices and open questions
6. docs/UI_SPEC.md: pages and design direction
7. PROGRESS.md: where we are right now

## What the system does

Four domain agents (Academic, Research, Placement, Finance) aggregate department data in parallel through one governed connector. A deterministic KPI engine turns that into institution-wide KPIs with targets and variance. An LLM drafts options and risks for every off-target KPI. A report node compiles a decision brief with drill-down evidence. A validation gate checks it, self-heals on failure within a bounded retry budget, and only then does a named human (Principal, Director or Registrar) approve, edit or override. Approved briefs are versioned, audited and reversible.

## Non-negotiable rules

1. The LLM never produces, computes or rounds a number. Figures come from the KPI engine and reach the text by reference tokens (`{{kpi:KEY}}`, `{{fact:ID}}`). See docs/ARCHITECTURE.md.
2. Agents draft and flag; a named human approves. Nothing is published without an approval record from an authorised role.
3. Every figure traces to a source: metric_fact id, source system, source ref, as_of date, status.
4. Provisional, forecast and unreconciled figures are never shown as final. A status badge is visible wherever such a figure appears.
5. A missed target is never hidden by rounding. Status is decided on unrounded values.
6. No agent touches a data source directly. Everything goes through the connector (MCP server).
7. Real data never leaves the machine. Hosted LLMs are allowed only when data_mode is synthetic, enforced in code and checked against the database, not only the env file. No LangSmith or any external tracing.
8. Retry is bounded (MAX_ATTEMPTS, default 3). On exhaustion, escalate to the human with a diagnosis. Never loop forever.
9. The audit log is append-only and hash-chained. Log inputs and outputs of every step, not only messages.
10. Validation is a hard gate. A draft reaches human review with a green report, or flagged `escalated` with its diagnosis once the retry budget is spent. An escalated draft can never be approved past a failed integrity check (V1, V4, V5, V6, V7, V9), only sent back or overridden. Completeness failures (V2, V3, V8) can be approved only with the approver's recorded acknowledgement (decision D13).
11. Percentages are aggregated from numerators and denominators, never by averaging department percentages.
12. Do not invent NIRF or NAAC definitions, parameter codes or targets. Use `PLACEHOLDER_PENDING_IQAC` markers until the university supplies them.

## Stack (provisional, see docs/DECISIONS.md)

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2
- Orchestration: LangGraph with LangChain components (checkpointer, interrupt, Send fan-out)
- Connector: MCP server (Python MCP SDK) with scoped tokens, consumed through langchain-mcp-adapters
- Storage: PostgreSQL 16 with pgvector
- LLM: local first (Ollama in dev, vLLM on a university GPU in production) behind one provider factory
- Frontend: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, ECharts, TanStack Query, SSE for run progress
- Tests: pytest, a FakeLLM for deterministic graph tests, Playwright for the approval flow smoke test
- Packaging: Docker Compose

Library APIs here change quickly (LangGraph, LangChain, MCP SDK, Next.js). Verify against current official docs before using any API, pin versions in lockfiles, and never rely on remembered signatures.

## Working agreement

- Start each session by reading PROGRESS.md and stating today's goal from docs/BUILD_PLAN.md. End each session by running the tests, updating PROGRESS.md and committing in small commits.
- Build vertical slices (data to KPI to brief to UI for one KPI) before widening.
- Write the tests first for the KPI engine and every validation check.
- When a design choice has real trade-offs, present 2 or 3 options with costs to Kiran. Do not converge silently. The provisional defaults in docs/DECISIONS.md can be changed; say so if one starts to hurt.
- Kiran must be able to explain and defend every part. Keep docs/VIVA_NOTES.md current: for each component, what it is, why this choice, which alternative was rejected, and the known weakness.
- Say plainly when something is weaker than it sounds.
- Do not add a dependency without a line in PROGRESS.md saying why.
- Never commit `.env`, anything under `data/real/`, or credentials.
- Do not claim a task is done until you have run it and seen it pass.
- No em dashes in docs, comments or messages to Kiran.

## Dev machine notes

Kiran develops on an Apple Silicon MacBook Air (no NVIDIA GPU). Check before assuming: Python 3.12 (Miniforge or uv), Node 20+, pnpm, Docker Desktop, Ollama. Local models on this machine are for development and debugging, so keep prompts small and structured and keep the FakeLLM path fast. Production inference targets a university GPU server whose specs are still unknown.

## Commands

Fill this in as the Makefile appears (`make dev`, `make seed`, `make test`, `make acceptance`, `make demo`).
