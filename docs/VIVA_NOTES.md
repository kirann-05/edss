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

**How do you know a HOD cannot see another department?**
Because the response does not contain it. A restricted department row carries its name and nothing else. A test signs in as a HOD, reads the raw JSON of the drill-down, domain and data-health responses, and checks that no other department's value, input or fact id is present, with a positive control proving the check can find them. A second test walks the route table, so a route added later that forgets to check the session fails on its own.

**What happens when a department has no data, or only unreconciled data?**
It is left out of that KPI and said so, in words, next to the figure. It is never counted as zero. The drill-down lists the unreconciled record with its badge and marks it as not used. This is deliberately strict (D24). The cost is that one unreconciled figure removes a department from a KPI, and the alternative of summing the final quarters only would risk an apples to oranges ratio.

**What is the weakest part?**
Update this with the truth as the build proceeds. Initial candidates: small local models and structured output reliability, dependence on how clean the university's data is, and the placeholder KPI definitions.

## Component notes (fill in during the build)

| Component | What it is | Why this choice | Rejected alternative | Known weakness |
| --- | --- | --- | --- | --- |
| KPI engine | Decimal-only engine. A KPI formula is YAML data, parsed with Python's own parser and checked against an allow-list (no eval). It computes one value per department and one for the institution, from totals, and decides status on the unrounded value | Auditable and reproducible: a figure never depends on a model. Tests carry the planted traps with exact expected values | Letting an LLM compute KPIs, or evaluating formulas with eval | A department is kept out of a KPI if any input it needs is missing or not final, so one unreconciled figure removes that department from that KPI (D24). `period_agg` and the 2 percent at-risk band are my defaults, not IQAC's. Citations can double count shared papers (D23) |
| Connector | | | | |
| Ingestion | Only the synthetic generator exists so far: deterministic (seed 42), calibrated to exact totals, with ten planted traps and one test each | The demo and the tests need known answers, so the data is built to have them | Random data with no traps, which would prove nothing | It is not real data, and its dates are relative to the day it is seeded, so it goes stale after 90 days until re-seeded. Real adapters, validation and rejection counts are still to build (F2) |
| Graph | | | | |
| LLM layer | | | | |
| Validation gate | | | | |
| Human gate | | | | |
| Versioning and rollback | | | | |
| Audit chain | | | | |
| RBAC | A permission matrix written out from SPEC section 2, plus a department scope. Scope is applied in one place, the view builders, so a restricted department row carries its identity and nothing else | The guarantee has to hold in what is sent, not in what the UI chooses to draw. A test reads raw response bodies as a HOD and a generic test walks every route | Hiding data in the UI only, or ad hoc checks in each route | Users are in memory with one shared synthetic password. No login lockout, no SSO. The demo sign-in exists only in synthetic mode and is covered by a test, but it is a deliberate bypass of passwords |
| Dashboard | Next.js against the real API, with types generated from its OpenAPI contract. Every status is an icon plus a label. Figures are exact decimal strings rounded by the UI with BigInt, and a missed target that rounds to equal is called out in words | Rules 4 and 5 made visible, and a contract that cannot drift quietly (D22) | The Streamlit prototype from Labs 1 and 2, which cannot do roles, a review queue or an audit view, and a mock API inside the browser | Light theme only, no axe or Playwright run yet, ECharts bundle size not measured, and it still runs against the in-memory synthetic store rather than Postgres |
