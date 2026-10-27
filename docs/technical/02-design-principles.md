# 2. Design principles

## 2.1 The twelve rules, and where the code enforces each

These are non-negotiable (`CLAUDE.md`). Each is enforced in code, not left to the prompt, and each has a test.

| # | Rule | Enforced in | Proved by |
| --- | --- | --- | --- |
| 1 | The language model never produces, computes or rounds a number. Figures reach text only as `{{kpi:KEY}}` or `{{fact:ID}}` tokens | `app/agents/tokens.py` (render and lint), check V1 in `app/agents/validation/checks.py` | `tests/agents/test_tokens.py`, fault "a figure written by hand" |
| 2 | Agents draft and flag; a named human approves | `GovernanceService.decide` and `approval_state` (`app/governance/service.py`), permission `approve` in `app/core/rbac.py`, check V5 | `tests/governance/test_governance.py` |
| 3 | Every figure traces to a source: record id, source system, reference, as-of date, status | `KpiFigure.input_fact_ids`, check V7, `/api/facts/{id}` | `tests/agents/test_validation.py` (V7) |
| 4 | Provisional, forecast and unreconciled figures are never shown as final, and carry a badge | KPI engine excludes non-final records (`app/kpi/engine.py`); check V4; status badges in the web app | traps T3, T4, T8 |
| 5 | A missed target is never hidden by rounding; status is decided on unrounded values | `app/kpi/engine.py`; check V6; `roundingHidesMiss` in `frontend/src/lib/format.ts` | trap T6 (74.96 against 75) |
| 6 | No agent touches a data source directly; everything goes through the connector | `Connector` protocol, MCP server (`app/mcp_connector/`), per-run scoped tokens | `tests/agents/test_architecture.py` forbids the imports; swap test in `tests/mcp_connector` |
| 7 | Real data never leaves the machine; hosted models only on synthetic data, checked against the database; no external tracing | `is_local_host` and the data-mode check in `app/agents/llm.py`, `SystemConfig.data_mode()` | `tests/agents/test_llm.py`, `tests/test_tracing_guard.py` |
| 8 | Retry is bounded (MAX_ATTEMPTS = 3), then escalate with a diagnosis | `after_validate` in `app/agents/graph.py`, `GraphDeps.max_attempts` | escalation tests in `tests/agents/test_graph.py` |
| 9 | The audit log is append-only and hash-chained, recording inputs and outputs of every step | `app/governance/audit.py`, `app/db/audit_store.py`, database role and trigger (migrations) | `tests/db/test_audit_store.py`, tamper test in `tests/api/test_audit_api.py` |
| 10 | Validation is a hard gate; integrity failures (V1, V4, V5, V6, V7, V9) can never be approved, completeness failures (V2, V3, V8) only with a recorded acknowledgement | `approval_state` in `app/governance/service.py` | `tests/governance/test_governance.py` (TestEscalated) |
| 11 | Percentages are built from numerators and denominators, never by averaging department percentages | formula grammar in `app/kpi/formulas.py` (`sum(...) / sum(...)`) | trap T7, `tests/kpi/test_formulas.py` |
| 12 | No invented NIRF or NAAC definitions, codes or targets | `PLACEHOLDER_MARKER` check in `app/kpi/loader.py`; NIRF and NAAC packs left empty | `tests/specialists/test_specialists.py` |

## 2.2 Software design principles applied

| Principle | How EDSS applies it |
| --- | --- |
| Separation of concerns, layered architecture | Web app, API, agent layer, connector, engine and data, model layer (`03-architecture.md`). Each layer only calls the one below it |
| Dependency inversion | The agent graph depends on two protocols, `Connector` and `ChatModel`, never on a concrete data source or model. The demo, the tests and production swap implementations without touching the graph |
| Single source of truth | Numbers only from the KPI engine; KPI definitions and targets as data (`app/kpi/definitions/*.yaml`); the API contract generated from code (`openapi.json`, frontend types) |
| Least privilege | Each run gets an MCP token for its plan's areas only; the app's database role cannot change the audit log; a HOD sees only their department |
| Fail safe | A check that cannot pass escalates to a person; a model that is down returns a clear 503; a mismatch between the env file and the database refuses to start |
| Immutability | Domain objects are frozen Pydantic models; fact batches and report versions are never changed, only superseded |
| Determinism and testability | The KPI engine is plain code with exact decimals; a FakeLLM gives canned, repeatable drafts; the synthetic data uses a fixed seed with ten planted traps |
| Defence in depth | Rules are enforced in the prompt, in code-side checks, in the validation gate, at the human gate, and in the database |
| Explicit over implicit | Missing data is said in words and never counted as zero; every figure shows its as-of date and status |
