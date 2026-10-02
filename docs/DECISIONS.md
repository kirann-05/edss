# DECISIONS

D1 to D4 were put to Kiran as options and have not been answered yet. Provisional defaults are set so the build can start on Day 1. They are changeable. The cost of changing each one later is stated. If a provisional default starts to hurt, present options to Kiran instead of working around it.

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

## Open questions for Kiran to answer or chase

1. Which departments are in the pilot, and does IQAC already have approved KPI definitions and targets? Is NIRF or NAAC the priority?
2. What GPU or server resources can the university IT cell provide, and who decides?
3. Does the university use SSO (Google Workspace, Microsoft, LDAP)?
4. Can the university run Docker on a server, and who hosts after the demo?
5. Does the professor expect specific KPIs or a specific brief format?
6. Who signs the Data Requirements Specification (HOD, Registrar or IQAC), and what is the realistic turnaround?
