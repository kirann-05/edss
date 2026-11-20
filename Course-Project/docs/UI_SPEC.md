# UI SPEC

Users are a Principal, Registrar, Deans and HODs. They read dashboards, review a draft brief and approve it. The UI should feel like a calm, trustworthy executive tool, not a developer console. Use the frontend-design skill for visual direction before building. Demo is likely on a projector, so default to a light theme with strong contrast and large type, and support dark mode only if time remains.

## Design direction

- Quiet and dense. Generous whitespace, tabular numerals, one accent colour, status colours reserved for status.
- Trust cues everywhere: as-of dates, source chips, status badges (final, audited, provisional, forecast, pending reconciliation), validation state.
- Never colour alone. Every status has a label and icon.
- Variance chips show direction and size, for example "3.4 pts below target". Missed is missed even when the rounded number looks like the target.
- Empty, loading, error and stale states designed for every panel. A stale or missing department is shown explicitly, never as zero.
- Responsive down to a laptop at 1280px. Mobile is not a goal.

## Pages

| Page | Purpose | Key elements |
| --- | --- | --- |
| Login | Sign in | Email and password, role shown after sign in |
| Dashboard | Institution view (panels from the book's 15.9) | KPI cards with target and variance, domain tabs with breakdown by department, drill-down drawer, current approved report card |
| Drill-down drawer | KPI to source | KPI, formula, version, inputs, per-department values and spread, fact list with status badges and source refs, link to data health |
| New Run | Request, clarify, plan | Chat-style clarifier, editable plan outline, lock button, live progress per node with timings |
| Review queue | Pending drafts | List with status, validation state, escalation flag, age |
| Brief review | The approval screen | Left: brief with KPI summary, options, risks, trade-offs, assumptions. Right tabs: Evidence, Validation report, Data health, Prior briefs. Bottom bar: Approve, Edit, Override (reason required) |
| Reports | Versions | Version list, status, approver, diff between versions, rollback button with confirmation, PDF export |
| Audit | Trust | Filter by run, actor, action, date. Chain verification status. Run trace timeline |
| Data health | Freshness | Matrix of department by domain with as-of, stale and missing flags, last ingest batch, refresh button |
| Admin | Users | Role assignment, scope grants for the Registrar |

## Interaction rules

- Edits to options happen inline in the brief review and are tracked as a diff. The approver sees what changed from the draft.
- Override and rollback require a reason and a confirmation dialog.
- Approve is disabled until validation is green or the draft is flagged escalated, and in the escalated case the approver must tick an acknowledgement.
- Live run progress uses SSE. Each node shows queued, running, done, failed, with elapsed time and, for the retry loop, the attempt number and the failing check.
- Every number in the UI is clickable to its drill-down.

## Accessibility

Keyboard navigable, visible focus, WCAG AA contrast, chart data available as a table toggle, status never conveyed by colour alone.

## Charts

ECharts. Bar for department comparison with target line, small multiples for trends across years, no pie charts, no gradient fills, direct labels over legends where possible. Read the dataviz skill before building any chart.
