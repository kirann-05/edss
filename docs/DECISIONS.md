# DECISIONS

D1 to D4 were put to Kiran as options. D1 is now decided (C5). D2 to D4 are still unanswered and keep their provisional defaults. They are changeable. The cost of changing each one later is stated. If a provisional default starts to hurt, present options to Kiran instead of working around it.

## Confirmed by Kiran (2026-10-03)

| ID | Decision | Notes |
| --- | --- | --- |
| C1 | Repo lives at `~/Claude/edss` | No spaces in the path. The old folder `~/Claude/Agentic AI ` (trailing space) only holds the original zip |
| C2 | Container runtime is OrbStack | Docker compatible and lighter on a 16 GB machine. The compose file stays plain Docker Compose so it runs on any Docker host later |
| C3 | D1 deferred: FakeLLM only until Day 4 | Build all plumbing on FakeLLM. Pick the real dev model by Day 4. The data_mode guard is built on Day 4 regardless |
| C4 | Lab grading format unknown | Kiran to ask the professor whether each lab is also submitted as a notebook. Until then, keep every lab's deliverable runnable from one command so it can be wrapped in a notebook later |
| C5 | D1 decided: local first | Ollama on the dev machine with `qwen3.5:4b` (chat, 3.4 GB) and `nomic-embed-text` (embeddings), both small enough for 16 GB alongside Postgres. FakeLLM stays the default for tests and the demo fallback. Production inference on a university GPU through vLLM, sized once IT answers (H3) |
| C6 | D13 to D24 confirmed as implemented | Confirmed 2026-10-03. Rule 10 in CLAUDE.md reworded to match D13 |
| C7 | Code is pushed to a private GitHub repo, kirann-05/edss, so CI runs on every push | Commits use the GitHub noreply address so the push is accepted with email privacy on. `.env`, `data/real/` and credentials stay out of git, checked before the first push |

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

## Review findings from 2026-10-03 (confirmed by Kiran, C6)

Each of these is a gap or contradiction found in the pack. The defaults below are what the build does, confirmed on 2026-10-03.

| ID | Issue | Decision |
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

## Build approach (confirmed by Kiran, C6)

### D22: Where the UI gets its data before Postgres and the graph exist

| Option | Upside | Cost |
| --- | --- | --- |
| A. Real FastAPI over in-memory services, fed by the synthetic generator and the real KPI engine. Types generated from its OpenAPI | One implementation. Auth, RBAC, SSE and schemas are the real ones from day 1. No throwaway mock layer. Contract drift is a compile error | The backend slice has to exist before the matching page can show real data. In-memory services are replaced later, one file each |
| B. Mock route handlers inside Next.js, hand-typed fixtures | UI can start in minutes with no backend at all | Throwaway code. Fixtures can disagree with the engine. Contract drift is found late. Auth, SSE and RBAC get built twice |
| C. MSW in the browser | No server needed, works offline | Same drift problem as B, plus one more dependency |

Decision: A, delivered as vertical slices so a page is usable as soon as its slice is done. Cost of changing later: low, the UI only talks to `/api/*` and does not know which backend answers.

## Implemented defaults (confirmed by Kiran, C6)

### D23: citations and shared papers

RS_CIT_PP divides total citations by unique publications, but citations are department-level facts, so a paper shared by two departments would be counted twice if both report its citations. The synthetic data credits a paper's citations to its lead department only, which avoids the double count. Real adapters must do the same, or `research_publication` needs a citations column. Confirm with IQAC together with D12.

### D24: how a department drops out of a KPI

| Option | Behaviour | Cost |
| --- | --- | --- |
| A. All or nothing per department (implemented) | A department is in a KPI only if every metric the formula needs has data and every record for it is final or audited. Otherwise it is listed as missing or excluded, with the reason | One unreconciled figure removes a department from that KPI |
| B. Partial sums over the final records | Use the quarters that are final, flag the gap | Shows more, but a ratio can mix unlike periods, for example two quarters of spend over a full-year budget |
| C. Fail the KPI | The institution figure is undefined if any department is incomplete | Too fragile, one late department blanks the whole dashboard |

Default A. Stale data is the exception: it is used and flagged, because old data is better flagged than silently dropped. Cost of changing later: low, it is one function in `kpi/engine.py`.

### Where D13 to D21 stand

| ID | Status |
| --- | --- |
| D13 escalated drafts cannot be approved past an integrity failure | In code, `INTEGRITY_CHECKS` in `governance/service.py`, tested through the API. Rule 10 in CLAUDE.md reworded to match |
| D14 `period_agg` per metric | In code, `kpi/catalogue.py` |
| D15 at-risk band | In code, `judge()` in `kpi/engine.py`, 2 percent default per definition |
| D16 formula grammar | In code, `kpi/formulas.py`. AC_PO uses a simple mean, flagged placeholder |
| D17 host check on the LLM base URL | In code, `is_local_host` and `get_chat_model` in `agents/llm.py`, checked at construction and on every call |
| D18 single writer for the audit chain | In code as a process lock, verified under 8 concurrent threads. The Postgres advisory lock arrives with F3 |
| D19 honest parallel benchmark | Not built. A test already asserts parallel beats sequential with simulated latency, the script that prints both timings is still to write |
| D20 seeded prior briefs | In code, `services/archive.py`, similarity by token overlap in memory. pgvector arrives with F5 |
| D21 number-word lint and structured direction | In code, `agents/tokens.py` flags digits and spelled-out numbers, and status and direction reach the text as tokens. The prose-truth gap stays a known weakness |

### Decisions made while building (2026-10-03 and 04)

| ID | Decision | Why | Cost |
| --- | --- | --- | --- |
| D25 | The plan's outline steps are written in code from the model's decisions, and the areas follow from the chosen KPIs | The pipeline is fixed, so a model must not be able to promise a step the graph does not run | The model cannot add a custom step. A person can still reword any step |
| D26 | A data refresh adds to the same ledger. A changed file is a new batch, an unchanged file adds nothing, and superseded records are kept | An approved brief cites record ids, and those must keep pointing at the same records | The ledger only grows. Cleaning it is a deliberate act, not part of a refresh |
| D27 | The model is checked twice: a cheap check with specific feedback right after it answers (so a small model can fix itself), then the nine checks as the gate | The gate alone makes a small model fail the long way round | The cheap check is ignored for the canned model, so injected faults still reach the gate |
| D28 | Commits use the GitHub noreply address, and the workflow file waits in `docs/ci` until the token has the `workflow` scope | GitHub refused a push that exposed a private email, and refused a workflow without the scope | CI does not run until Kiran grants the scope |
| D29 | Confirmed by Kiran (2026-10-05). The connector is an MCP server mounted inside the API process at `/mcp`, and the graph reaches it over real HTTP with a token minted for each run. Options weighed: (a) in-process MCP client, no HTTP: simplest, but no real protocol or token on the wire; (b) a separate connector process: a true process boundary, but it needs its own copy of the in-memory data and a refresh must reach both; (c) mounted in the API (chosen) | Real protocol, real tokens and one audit row per call, with one copy of the data, so a refresh reaches both at once. Once PostgreSQL holds the data, (b) is a second entry point, not a rewrite | No process boundary yet: the guarantee is that agent code only holds an MCP client and a scoped token. One more HTTP hop per read, a few milliseconds |
| D30 | Confirmed by Kiran (2026-10-05). The planner is rules first and the model second. Word rules decide wherever the request says something; the model is asked only about what they cannot read; where the model thinks something was said that no word says, the person is asked, and told why; an unusable model answer falls back to the rules, while a model server that is down is reported at once, because drafting will need it. Whether to draft options for every KPI is never the model's guess | Measured: the model alone asked the right questions 4 of 10 times and planned 4 of 6 right, the rules 9 of 10 and 6 of 6. The hybrid scores 9 of 10 and 6 of 6 with 6 model calls instead of 16, and a model that answers nonsense no longer stops planning | With this model the rules do the work. A paraphrase the rules do not know is asked about rather than guessed. Revising a plan in words still uses the model |
| D31 | Confirmed by Kiran (2026-10-05). With `EDSS_DATABASE=true`, people, grants and the data come from PostgreSQL at start, the services keep their rules in memory, and every change is written through at once. The data mode alone is read from the table on every call | One place for each rule, and the database is the record that survives a restart. Rule 7's mode check reads the database itself, so a change there takes effect immediately | It assumes one API process: a second process would not see the first one's in-memory changes until it restarted. Since L5e and L5f the audit log, runs, briefs and versions are there too. Since L5g the graph's checkpoints are there too, so a run stopped by a restart is resumed from its last step. Refreshing data from the web page and the demo reset are refused in this mode |
| D32 | Confirmed by Kiran (2026-10-05). Synthetic and real records live in the same tables. The first real load switches the database to real mode, after which the synthetic records are kept, archived, and never read; the synthetic personas are switched off; and the app refuses to start unless `DATA_MODE` matches the stored mode | Nothing is deleted, as the data contract asks, and one database is backed up | Every read filters by mode. Going back to synthetic would be a deliberate act on the database, not a setting |
| D33 | Confirmed by Kiran (2026-10-05). The departments in the real manifest become the list the app shows, in its order. Synthetic departments stay in the table, off the list | The university's own list decides, from its own files | A department dropped from the manifest disappears from the app at the next load. Its records stay |
| D34 | Confirmed by Kiran (2026-10-05). Real data is loaded from the command line only (`scripts/ingest.py --db`), and the first administrator is created there too (`scripts/create_user.py`) | No upload page to harden, and loading is done by the people who run the server, with a row in the audit log each time | The Registrar cannot load data from the browser |

## Open questions for Kiran to answer or chase

1. Which departments are in the pilot, and does IQAC already have approved KPI definitions and targets? Is NIRF or NAAC the priority?
2. What GPU or server resources can the university IT cell provide, and who decides?
3. Does the university use SSO (Google Workspace, Microsoft, LDAP)?
4. Can the university run Docker on a server, and who hosts after the demo?
5. Does the professor expect specific KPIs or a specific brief format?
6. Who signs the Data Requirements Specification (HOD, Registrar or IQAC), and what is the realistic turnaround?
