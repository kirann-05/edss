# SPEC: Executive Decision Support System

Derived from Chapter 15 of the 14-Lab Build Book (docs/source/chapter15.md). Where the book is inconsistent or leaves a gap, this document decides and says so (section 9).

## 1. Problem

Leadership reviews academic, research, placement and finance performance from separate departmental reports that arrive on different schedules and formats. There is no single real-time view of institution-wide KPIs against NIRF, NAAC and strategic-plan targets. Consolidated reports are weeks old by the time the Governing Council sees them. Drilling from a KPI to a department or root cause means going back to each department. Provisional or unreconciled figures get mistaken for final.

## 2. Users and roles

| Role | Can do |
| --- | --- |
| Registrar | Authorise data scope, start runs, review, approve, rollback, view audit |
| Principal / Director | Start runs, review, approve, edit, override, view all dashboards and audit |
| Dean | Start runs, view institution dashboards, view department detail within their school |
| HOD | View own department detail and institution KPIs, cannot approve |
| Viewer (Governing Council) | View approved, published reports only |
| Admin | Manage users and roles, view system health, cannot approve or edit content |

Department-level detail is traceable but access-controlled. A HOD never sees another department's record-level detail.

## 3. Scope

In scope: ingestion from files and read-only SQL, connector, KPI engine, agent graph, validation gate, human gate, governed publish with rollback, dashboard with drill-down, audit viewer, data health, PDF export, role-based access.

Out of scope for the 3 weeks unless time remains: SSO, Governing Council email distribution, multi-institution tenancy, streaming ingestion, mobile app.

## 4. Functional requirements

| ID | Requirement | Lab |
| --- | --- | --- |
| FR-1 | Free-text request, then the agent asks at least 2 clarifying questions, then proposes an editable plan that is locked before work begins | 1, 3 |
| FR-2 | Access check: each domain must have a Registrar-authorised read scope before the run starts | 5, 12 |
| FR-3 | Four domain agents aggregate in parallel and return a typed DomainView with data-health flags | 7, 8 |
| FR-4 | KPI synthesis from approved definitions with target and variance, computed deterministically | 2 |
| FR-5 | Decision brief: KPI summary, options and risks for every off-target KPI, explicit assumptions, data health section | 3, 9 |
| FR-6 | Drill-down: KPI to domain metric to department to source record reference | 9 |
| FR-7 | Validation gate with checks V1 to V9, targeted regeneration within MAX_ATTEMPTS, escalation on exhaustion | 10, 11 |
| FR-8 | Human gate: approve, edit or override with a required reason, role-checked | 12 |
| FR-9 | Governed publish: immutable versions, current pointer, one-click rollback | 12 |
| FR-10 | Dashboard with four panels: institution KPIs with variance, domain metrics, drill-down evidence, executive report | 14 |
| FR-11 | Data health: freshness, stale and missing flags per department per domain | 9 |
| FR-12 | Audit viewer and run trace, filterable | 6 |
| FR-13 | Checkpoint and resume of a crashed run | 6 |
| FR-14 | PDF export of an approved version | 14 |
| FR-15 | Role-based access, including HOD scoping | 12 |
| FR-16 | Ingestion with validation, on-demand refresh and optional schedule | 5 |

## 5. KPI model

- KPI definitions are data (versioned rows with a formula over metric keys), not code. Only active, approved definitions are used.
- Aggregate from numerators and denominators. Institution pass percentage is total passed over total appeared, not the mean of department percentages.
- A zero denominator makes the KPI undefined. It is shown as undefined, never as 0 or 100.
- Status (met, at_risk, missed) is computed on unrounded values. Display rounding must never flip a status.
- Each KPI result stores formula version and the list of input metric_fact ids.
- Seed KPIs in docs/DATA_CONTRACT.md are placeholders to be replaced by the university's approved list.

## 6. Guardrails

From section 15.12 and 15.4 of the book, plus the project rules in CLAUDE.md:

- Do not circulate an institution-wide KPI or report without Principal, Director or Registrar approval.
- Keep department detail traceable but access-controlled.
- Never present a forecast, provisional or unreconciled number as final.
- Use only approved KPI definitions and targets. Show the formula and source behind every KPI.
- Version every executive report and keep an audit log of circulation.
- Academic: pull only from approved records, show the spread, flag stale or missing departments.
- Research: never double-count a cross-department collaboration.
- Placement: never present a provisional offer as a confirmed placement.
- Finance: use audited or approved figures only, never project a forecast as an actual, flag figures pending reconciliation.
- KPI: never mask a missed target in a rounded figure.

## 7. Validation checks (the acceptance gate)

Deterministic checks. LLM judging is allowed only as an extra signal, never as the gate.

| ID | Check | How |
| --- | --- | --- |
| V1 | Every figure cites its source | Every number in the rendered brief resolves to a kpi_result or metric_fact with a source. LLM text may contain digits only inside reference tokens or an allowlist (financial year labels, dates) |
| V2 | Assumptions are stated explicitly | Each option has a non-empty assumptions list, and the brief has an assumptions section listing as-of dates and stale flags |
| V3 | Each option lists risks and trade-offs | Non-empty risks and trade_offs on every option |
| V4 | No non-final figure presented as final | Any input with status provisional, forecast or pending_reconciliation carries a badge and is not described as actual or final |
| V5 | No action without approval | Brief stays draft until an approval record from an authorised role exists, and publish refuses otherwise |
| V6 | Only approved definitions, no masked misses | Each KPI uses an active approved definition, and status was computed unrounded |
| V7 | Drill-down is traceable | Every KPI resolves to fact ids that resolve to a source reference |
| V8 | Coverage | Every KPI in the locked plan is present and stale or missing departments are flagged |
| V9 | No double counting | Cross-department publications counted once at institution level |

Failures return a locator (kpi_key, option_id or section) so only the failing part is regenerated.

## 8. Success metrics and definition of done

- 100% of validation checks pass before human review, measured by `make acceptance`.
- Every brief is grounded in verified data with an evidence record per figure.
- Zero consequential actions without approval, a complete audit trail, and one-click rollback demonstrated.
- Failure injection: at least 8 injected faults, all detected, repaired within budget or escalated.
- Parallel domain aggregation measurably beats sequential on wall-clock time (benchmark script).
- On a real case, the Principal produces an approved, validated brief in one session with light edits.

## 9. Where the book contradicts itself or leaves gaps

| Issue | Decision |
| --- | --- |
| Text says the four domain agents run in parallel, but the pseudocode and message map chain them sequentially | Run in parallel with a join barrier before KPI synthesis |
| Pseudocode puts human review before validation, text says validation is a hard gate before review | Validation first, then human gate |
| Worked example and Lab 8 describe best-of-N candidate merging, which suits content generation, not KPI math | Lab 8 becomes per-domain parallel fan-out plus per-KPI parallel options drafting, merged deterministically by plan coverage. Optional best-of-N only for options text |
| Lab 13 describes domain packs for a generation node | Specialists are framework packs (NIRF, NAAC, Strategic plan) that supply definitions, targets, narrative templates and risk heuristics |
| Book assumes real-time data | Freshness equals the ingestion cadence. Every figure shows an as-of date. Honest wording in the demo |
| Book names a Registrar-authorised access gate but not how | Per-domain scope records created by the Registrar role, checked at run start |

## 10. Non-goals

The system does not decide anything for leadership. Options are drafts with stated trade-offs, not recommendations of fact.
