# 4. Design patterns

Each pattern below is used in the code, at the place named. Class diagrams: `uml/png/04_class_agents.png`, `uml/png/05_class_services.png`.

| # | Pattern | Where | Why it is there |
| --- | --- | --- | --- |
| 1 | **Strategy** (via a protocol) | `ChatModel` protocol with `FakeLLM` and `RemoteModel` (`app/agents/llm.py`, `fake_llm.py`) | The graph asks for words the same way whether the model is canned (demo, tests) or a local Ollama or vLLM server |
| 2 | **Factory Method** | `get_chat_model(...)` in `app/agents/llm.py`; `create_app()` in `app/main.py`; `build_graph()` in `app/agents/graph.py` | One place decides which model, which stores (memory or PostgreSQL) and which connector to build, from settings, and refuses a hosted model on real data |
| 3 | **Adapter** | `SourceAdapter` with `CsvAdapter` and `SqlAdapter` (`app/ingestion/adapters.py`); `McpConnector` adapting MCP calls to the `Connector` protocol (`app/mcp_connector/client.py`) | Different university sources look the same to the ledger; the graph never knows it is talking MCP |
| 4 | **Proxy** | `RunConnector` (`app/mcp_connector/context.py`) | Stands in for the connector and forwards each call with the current run's scoped token, taken from a context variable |
| 5 | **Repository** | `DbAuditLog`, `RunRows`, `GovernanceRows`, `UserRows`, `ScopeRows`, `DbArchive` (`app/db/*.py`) | Services work with domain objects; how they are stored (memory or PostgreSQL) is hidden behind one interface each |
| 6 | **Observer (publish and subscribe)** | `RunEvents` (`app/agents/runtime.py`) streamed to the browser by the SSE endpoint `/api/runs/{id}/events` | Each graph step publishes an event; the run page subscribes and draws live progress |
| 7 | **Specification** | The nine checks V1 to V9, each a function from brief and context to violations (`app/agents/validation/checks.py`), run in order by `validate()` | Each rule is one small, separately tested predicate; the gate is their conjunction |
| 8 | **State machine** | `RunStatus` (clarifying, planning, running, awaiting review, completed, failed) and `BriefStatus` (draft, escalated, published, overridden, returned, rolled back) | Only legal transitions are allowed, and each is audited. Diagrams: `uml/png/09_state_run.png`, `uml/png/10_state_brief.png` |
| 9 | **Registry** | `@register(task)` handlers in `FakeLLM` (`app/agents/fake_llm.py`); `SpecialistRegistry` (`app/specialists/__init__.py`) | New tasks and framework packs are added by registration, without changing the code that looks them up |
| 10 | **Decorator** | `_persists` on `RunService` methods (`app/services/runs.py`) | Writes every change through to the database after the method runs, without each method repeating it |
| 11 | **Scatter and gather (fan-out, fan-in)** | LangGraph `Send` to four `domain_agent` nodes and one `draft_options` per KPI, joined at `kpi_synthesis` and `report_compose` (`app/agents/graph.py`) | Parallel work with a deterministic merge; measured 4.0 times faster |
| 12 | **Dependency injection** | `GraphDeps` (connector, model, runtime, draft sink) passed into the graph; FastAPI `Depends` for state, sessions and permissions (`app/api/deps.py`) | Tests inject fakes; the API checks a permission by declaring it |
| 13 | **Memento** | LangGraph checkpoints in PostgreSQL (`app/db/checkpoints.py`) | A stopped run resumes from its last completed step |
| 14 | **Command** | `Decision` objects (approve, edit, override, send back) handled by `GovernanceService.decide` | A decision is data: validated, role-checked, audited and replayable |

The hash-chained audit log is not a GoF pattern but a well-known integrity technique: each row stores the SHA-256 of the previous row with its own content, so changing any row breaks every hash after it (`app/governance/audit.py`).
