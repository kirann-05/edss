# DECISIONS

D1 to D4 were put to Kiran as options. D1 is deferred to Day 4 (see "Confirmed by Kiran"). D2 to D4 are still unanswered and keep their provisional defaults. They are changeable. The cost of changing each one later is stated. If a provisional default starts to hurt, present options to Kiran instead of working around it.

## Confirmed by Kiran (2026-10-03)

| ID | Decision | Notes |
| --- | --- | --- |
| C1 | Repo lives at `~/Claude/edss` | No spaces in the path. The old folder `~/Claude/Agentic AI ` (trailing space) only holds the original zip |
| C2 | Container runtime is OrbStack | Docker compatible and lighter on a 16 GB machine. The compose file stays plain Docker Compose so it runs on any Docker host later |
| C3 | D1 deferred: FakeLLM only until Day 4 | Build all plumbing on FakeLLM. Pick the real dev model by Day 4. The data_mode guard is built on Day 4 regardless |
| C4 | Lab grading format unknown | Kiran to ask the professor whether each lab is also submitted as a notebook. Until then, keep every lab's deliverable runnable from one command so it can be wrapped in a notebook later |

## Provisional (Kiran to confirm)

### D1: Where the LLM runs

| Option | Upside | Cost |
| --- | --- | --- |
| A. Fully local (Ollama in dev, vLLM on a university GPU) | Data never leaves campus | Needs roughly 10 to 24 GB VRAM for a 14B to 30B class model. Weaker structured output from small models |
| B. Hosted API in development on synthetic data only, local for real data | Faster to build, stronger model while developing | Needs a clean provider switch from day one and strict guard against real data on the hosted path |
| C. Small local model on CPU or laptop only | No infrastructure ask | Slow, weakest structured output |

Provisional default: B in practice, built on A's interface. Develop on whichever is available behind the same factory, with the data_mode guard making a hosted call with real data impossible. Cost of changing later: low, because the factory is one file.

### D2: Orchestration framework

| Option | Fit |
| --- | --- |
| A. LangGraph with LangChain components | Maps almost node for node to the book. Steepest learning curve |
| B. LangChain with custom orchestration | Easier start, hand-built checkpointing, retry bounds and gate |
| C. CrewAI, AutoGen or an agent SDK | Quick role demos, approval gate and resume less natural |

Provisional default: A. Cost of changing after Day 7: high, the graph is the spine.

### D3: Frontend

| Option | Fit |
| --- | --- |
| A. Next.js with Tailwind, shadcn/ui, ECharts | Real multi-role app, best for drill-down and review queue. Most work |
| B. Vite React single page app | Lighter, routing and auth by hand |
| C. Streamlit or Chainlit | Fastest, but weak on roles, review queue and audit UX, reads as a prototype |

Provisional default: A. Cost of changing after Day 6: high.

### D4: Scope for 3 weeks

- Core: connector, store, KPI engine, 4 parallel domain agents, options and risks, validation gate with bounded retry, human gate, versioning with rollback, audit chain, dashboard with drill-down.
- Strong: failure-injection suite, RBAC with HOD scoping, framework specialists, resume from checkpoint.
- Stretch: SSO, scheduled refresh, Council distribution, evaluation metrics view.

Provisional default: Core plus Strong, Stretch only if ahead. Revisit at the Day 7 and Day 14 cut decisions.

## Decided (design principles, change only with a reason written here)

| ID | Decision | Why |
| --- | --- | --- |
| D5 | PostgreSQL with pgvector | One store for facts, audit, checkpoints and embeddings, real-world credible |
| D6 | Ingest then serve, not live read through the connector | Reproducible runs, stable evidence ids |
| D7 | Aggregate percentages from numerators and denominators | Averaging department percentages is wrong |
| D8 | KPI formulas are data, evaluated by a restricted evaluator | Auditable, no code injection, definitions can change without a release |
| D9 | Numbers by reference tokens | Makes hallucinated figures detectable and impossible to render |
| D10 | The Coordinator is the graph plus runtime wrapper, not a separate LLM | Honest and simpler, easier to defend |
| D11 | Validation before the human gate | The book's text, not its pseudocode |
| D12 | Cross-department paper credit: once at institution, credited to each department | Needs IQAC confirmation |

## Open issues from the 2026-10-03 doc review (proposed defaults, Kiran to confirm)

Each of these is a gap or contradiction found in the pack. The proposed default is what the build will do unless Kiran says otherwise.

| ID | Issue | Proposed default |
| --- | --- | --- |
| D13 | CLAUDE.md rule 10 says nothing reaches review without a green report, but ARCHITECTURE sends exhausted retries to the human as `escalated`. As written, an approver could publish a brief that failed V1 | Escalated drafts do reach the human, but Approve is blocked if any integrity check failed (V1, V4, V6, V7, V9). Only send back or override is possible then. Approve with acknowledgement is allowed only when the remaining failures are completeness checks (V2, V3, V8). Reword rule 10 to match |
| D14 | No rule for combining sub-periods (semesters, quarters) into a year, or for flows versus snapshots | Add `period_agg` (`sum` or `latest`) to every metric key in the catalogue. Flows such as expenditure sum. Snapshots such as faculty_count and budget_sanctioned take the latest as_of. KPIs are computed per period_year |
| D15 | `at_risk` is used but never defined. T6 (74.96 against 75) must be `missed`, so at_risk cannot mean "missed by a little" | `at_risk` means the target is met but the margin is under a per-KPI band, default 2% of target. Respects `higher_is_better` |
| D16 | The formula language cannot express the seed KPIs (weighted means, unique publications), and CO and PO weighting has no weight metric | Evaluator supports `sum`, `ratio`, `weighted_mean(value_key, weight_key)` and `unique_publications()`. AC_CO weights by `acad.courses_total`. AC_PO uses a simple mean across departments, flagged placeholder, until IQAC says how programmes are weighted |
| D17 | The hosted-LLM guard keys on the provider name, but `openai_compat` can point at any URL | When data_mode is real, the factory also checks the base URL host against an allowlist of local hosts (localhost and the configured university server), whatever the provider is called |
| D18 | Parallel nodes append to the hash-chained audit log at the same time and would race on `prev_hash` | Audit append takes a Postgres transaction-level advisory lock, so the chain has a single writer |
| D19 | Domain nodes are deterministic and read a local store, so parallel versus sequential differs by milliseconds | The benchmark reports raw timings and timings with configurable simulated source latency, labelled as such. Say this plainly in the viva |
| D20 | Lab 4 retrieves similar past briefs, but the synthetic data has none | The synthetic generator also seeds 3 to 5 prior approved briefs with the decisions leadership took |
| D21 | V1's digit lint misses spelled-out numbers, and no check confirms prose direction ("improved" when the KPI fell). V4's keyword check is brittle | Extend V1 to number words. The LLM receives status and direction as structured fields and refers to them by token. Record the remaining prose-truth gap as a known weakness in VIVA_NOTES |

## Provisional build approach (2026-10-03, Kiran to confirm)

### D22: Where the UI gets its data before Postgres and the graph exist

| Option | Upside | Cost |
| --- | --- | --- |
| A. Real FastAPI over in-memory services, fed by the synthetic generator and the real KPI engine. Types generated from its OpenAPI | One implementation. Auth, RBAC, SSE and schemas are the real ones from day 1. No throwaway mock layer. Contract drift is a compile error | The backend slice has to exist before the matching page can show real data. In-memory services are replaced later, one file each |
| B. Mock route handlers inside Next.js, hand-typed fixtures | UI can start in minutes with no backend at all | Throwaway code. Fixtures can disagree with the engine. Contract drift is found late. Auth, SSE and RBAC get built twice |
| C. MSW in the browser | No server needed, works offline | Same drift problem as B, plus one more dependency |

Provisional default: A, delivered as vertical slices so a page is usable as soon as its slice is done. Cost of changing later: low, the UI only talks to `/api/*` and does not know which backend answers.

## Open questions for Kiran to answer or chase

1. Which departments are in the pilot, and does IQAC already have approved KPI definitions and targets? Is NIRF or NAAC the priority?
2. What GPU or server resources can the university IT cell provide, and who decides?
3. Does the university use SSO (Google Workspace, Microsoft, LDAP)?
4. Can the university run Docker on a server, and who hosts after the demo?
5. Does the professor expect specific KPIs or a specific brief format?
6. Who signs the Data Requirements Specification (HOD, Registrar or IQAC), and what is the realistic turnaround?
