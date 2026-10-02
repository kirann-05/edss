# VIVA NOTES

Kiran must be able to explain and defend everything. Claude Code keeps this file current: when a component is built, add what it is, why, the rejected alternative, and the known weakness. The questions below are seeded now with honest answers. Replace claims with measured numbers as they exist.

## Likely questions

**Why agents at all, instead of a dashboard with SQL?**
The agentic parts are the clarify and plan loop, parallel domain agents, drafting options and risks, self-healing validation and the human gate. The arithmetic is deliberately not agentic, because a KPI that depends on an LLM is a KPI nobody can audit. Honest weakness: the LLM surface is narrow, and a sceptic could say most of this is a pipeline. The answer is that the narrow surface is the design, and the agent loop earns its place in planning, drafting and repair.

**How do you stop it hallucinating numbers?**
The LLM never writes numbers. It writes reference tokens that a renderer resolves from the database, and check V1 rejects any stray digit. Failure injection proves it: we inject a fake figure and the gate catches it. Cite the measured detection rate.

**Is it really real-time?**
It is as fresh as each source. Ingestion runs on a schedule and on demand, and every figure shows an as-of date. Finance may be quarterly. We flag stale data instead of pretending. Weakness: no streaming from source systems.

**Why LangGraph and not plain Python or CrewAI?**
The book's design needs a bounded back-edge, parallel fan-out, checkpoint and resume, and a human interrupt. LangGraph provides each natively. Plain Python means rebuilding all four. CrewAI is role-centric and makes the approval gate and resume awkward. Weakness: LangGraph's API moves quickly, so versions are pinned.

**Why is the Coordinator not a separate agent?**
Its job is state, plan, budgets and audit. That is control logic, and putting an LLM there adds risk without benefit. It is the graph plus the runtime wrapper.

**What if the LLM drafts a bad option?**
Options are labelled drafts with stated assumptions, risks and trade-offs, cite KPI references, and pass through a human who can edit or override. The system never acts on them.

**What about privacy of university data?**
Aggregated department data first, no personal identifiers requested, local models only for real data, enforced in code against the database setting, no external tracing, role-based access with HOD scoping, hash-chained audit.

**How does it scale to other departments?**
Departments and KPI definitions are data. Sources are adapters. Adding a department is a data change. What changes at larger scale: a single node database and one LLM server, which is fine for tens of departments, and the next step would be queueing runs and caching.

**Why did you not do best-of-N like the book's Lab 8?**
Best-of-N makes sense for generated content, not for deterministic KPIs. We parallelise across domains and across KPIs and merge by plan coverage. Best-of-N is optional for option wording only.

**How do you know it works?**
The acceptance suite (checks V1 to V9), the planted-trap fixtures with exact expected values, the failure injection suite, the parallel benchmark, and an end-to-end test of approve, publish and rollback.

**Are the KPIs the real NIRF and NAAC ones?**
Only once IQAC supplies approved definitions. Until then the seed definitions are marked placeholders, and the system is built so swapping them is a data change. Say this plainly.

**What is the weakest part?**
Update this with the truth as the build proceeds. Initial candidates: small local models and structured output reliability, dependence on how clean the university's data is, and the placeholder KPI definitions.

## Component notes (fill in during the build)

| Component | What it is | Why this choice | Rejected alternative | Known weakness |
| --- | --- | --- | --- | --- |
| KPI engine | | | | |
| Connector | | | | |
| Ingestion | | | | |
| Graph | | | | |
| LLM layer | | | | |
| Validation gate | | | | |
| Human gate | | | | |
| Versioning and rollback | | | | |
| Audit chain | | | | |
| RBAC | | | | |
| Dashboard | | | | |
