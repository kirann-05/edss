# 11. Traceability: requirement to module to test

Every requirement in `01-requirements.md`, the module that meets it (`07-detailed-design.md`), and the tests that prove it. Backend test paths are under `backend/tests/`; browser tests under `frontend/e2e/`.

| Requirement | Module | Proved by |
| --- | --- | --- |
| FR-1 Clarify, plan, edit, lock | M3 | `agents/test_plan_skill.py`, `agents/test_hybrid_planner.py`, `api/test_runs_api.py`, rehearsal step 2 |
| FR-2 Access check before a run | M4 | `api/test_admin_api.py` (a revoked area stops a run), `mcp_connector/test_scope.py` |
| FR-3 Four domain agents in parallel | M4 | `agents/test_graph.py` (TestParallelism), `make benchmark` |
| FR-4 Deterministic KPI synthesis | M2 | `kpi/test_engine.py`, `kpi/test_formulas.py`, `synthetic/test_trap_checks.py` |
| FR-5 Decision brief | M5, M6 | `agents/test_compose.py`, `agents/test_options_skill.py` |
| FR-6 Drill-down to source | M2, M6 | `api/test_kpi_api.py`, `agents/test_validation.py` (V7), rehearsal step 4 |
| FR-7 Validation gate, repair, escalation | M6 | `agents/test_validation.py`, `agents/test_repair.py`, `agents/test_graph.py`, `make acceptance` (94 of 94) |
| FR-8 Human gate | M7 | `governance/test_governance.py`, `api/test_briefs_api.py`, `e2e/approval-flow.spec.ts`, `e2e/edit-refused.spec.ts` |
| FR-9 Versions and rollback | M7 | `governance/test_governance.py` (TestVersionsAndRollback, TestFigureDiff), `api/test_reports_api.py` |
| FR-10 Dashboard | web app | `e2e/sign-in.spec.ts`, `e2e/keyboard.spec.ts`, rehearsal steps 1 and 4 |
| FR-11 Data health | M9 | `api/test_data_health_api.py`, `e2e/refresh.spec.ts` |
| FR-12 Audit viewer and trace | M8 | `api/test_audit_api.py`, `db/test_audit_store.py`, `governance/test_audit.py` |
| FR-13 Checkpoint and resume | M4 | `agents/test_graph.py`, `api/test_on_database.py` (restart keeps work) |
| FR-14 PDF export | web app | print view of a report (`frontend/src/components/reports/version-view.tsx`) |
| FR-15 Roles and scoping | API | `api/test_authorization.py` (walks every route), `api/test_scoping.py`, `e2e/scoping.spec.ts` |
| FR-16 Ingestion and refresh | M1 | `ingestion/*`, `api/test_refresh_api.py`, `make seed` (all ten traps) |
| FR-17 Real data loading | M1 | `db/test_real_data.py`, `db/test_create_user.py`, `ingestion/test_ingest_script.py` |
| FR-18 Similar prior briefs | M10 | `db/test_archive_store.py`, `api/test_archive_publish.py` |
| NFR-1 No model-written numbers | M5, M6 | `agents/test_tokens.py`, V1 fault trials |
| NFR-2 Traceability | M6 | V7 tests, dropped-source fault trials |
| NFR-3 Honest figures | M2, M6 | traps T3, T4, T6, T8; V4 and V6 fault trials |
| NFR-4 Privacy | model layer | `agents/test_llm.py`, `test_tracing_guard.py`, `db/test_real_data.py` (hosted model refused) |
| NFR-5 Accountability | M8 | `db/test_audit_store.py` (role and trigger), tamper test in `api/test_audit_api.py` |
| NFR-6 Reliability | storage | `db/test_backup.py`, `api/test_on_database.py`, `make smoke` |
| NFR-7 Security | API | `test_throttle.py`, `api/test_auth.py`, `test_health.py` (headers), `e2e/headers.spec.ts` |
| NFR-8 Performance | M4 | `make benchmark` |
| NFR-9 Accessibility | web app | `e2e/accessibility.spec.ts` (axe), `e2e/keyboard.spec.ts` |
| NFR-10 Maintainability | all | `make coverage` (98 percent), `make check` lint and types |
| NFR-11 Portability | deployment | `make smoke` |
| NFR-12 Local inference | model layer | `agents/test_real_model_skills.py`, `docs/evals` |

## The ten planted traps

| Trap | What it tests | Test |
| --- | --- | --- |
| T1 | Stale department flagged | `synthetic/test_trap_checks.py` |
| T2 | Missing department never counted as zero | same |
| T3 | Provisional offers kept out | same |
| T4 | Forecast never added to actuals | same |
| T5 | Shared paper counted once | same |
| T6 | 74.96 against 75 is missed | same |
| T7 | Percentages from totals | same |
| T8 | Unreconciled figure badged and excluded | same |
| T9 | Nothing to divide by gives no value | same |
| T10 | Two missed, one at risk | same |
