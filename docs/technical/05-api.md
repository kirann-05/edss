# API reference

Generated from the app's own routes by `scripts/build_api_doc.py` (run `make tech-docs`); do not edit by hand.
Every path is under `/api` on the web app's origin. Sign-in is an HttpOnly session cookie. A missing session
answers 401, a missing permission 403. Roles come from `backend/app/core/rbac.py`; a HOD or Dean also only ever
sees their own department's or school's detail, whatever the endpoint. The machine-readable contract is
`backend/openapi.json`, and the MCP connector's tools are listed in `03-architecture.md`.

48 operations.


## Admin

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/admin/options` | Options | Anyone signed in |
| GET | `/api/admin/scope-grants` | Scope grants | Registrar (`manage_scope`) |
| POST | `/api/admin/scope-grants` | Grant | Registrar (`manage_scope`) |
| POST | `/api/admin/scope-grants/{domain}/revoke` | Revoke | Registrar (`manage_scope`) |
| GET | `/api/admin/users` | Users | Admin (`manage_users`) |
| POST | `/api/admin/users` | Create user | Admin (`manage_users`) |
| PATCH | `/api/admin/users/{user_id}` | Update user | Admin (`manage_users`) |
| POST | `/api/admin/users/{user_id}/password` | Reset password | Admin (`manage_users`) |

## Audit

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/audit` | Newest first. Filtering never changes what the chain check covers. | Registrar, Principal (`view_audit`) |
| GET | `/api/audit/actions` | Actions | Registrar, Principal (`view_audit`) |
| GET | `/api/audit/verify` | Verify | Registrar, Principal (`view_audit`) |

## Auth

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| POST | `/api/auth/demo-login` | One-click sign-in for the seeded synthetic users, so a demo can switch roles quickly. | Public |
| GET | `/api/auth/demo-users` | Demo users | Public |
| POST | `/api/auth/login` | Login | Public |
| POST | `/api/auth/logout` | Logout | Public |
| GET | `/api/auth/me` | Me | Anyone signed in |

## Briefs

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/briefs` | List briefs | Registrar, Principal (`review`) |
| GET | `/api/briefs/{brief_id}` | Get brief | Registrar, Principal (`review`) |
| POST | `/api/briefs/{brief_id}/check-edits` | A dry run: would these edits pass validation? Nothing is saved or published. | Registrar, Principal (`review`) |
| POST | `/api/briefs/{brief_id}/decision` | Approve, edit, override or send back. The governance service checks the role, and logs a | Anyone signed in |
| GET | `/api/briefs/{brief_id}/evidence` | Evidence | Registrar, Principal (`review`) |
| GET | `/api/briefs/{brief_id}/prior` | Prior | Registrar, Principal (`review`) |

## Data health

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/data-health` | Data health | Registrar, Principal, Dean, HOD, Admin (`view_data_health`) |
| POST | `/api/data/refresh` | Read the sources again (FR-16). The data in use is replaced only when the whole read worked. | Registrar, Admin (`refresh_data`) |

## Demo

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| POST | `/api/demo/reset` | Start the demo again from its ready-made state. Everything made since is discarded. | Registrar, Admin (`refresh_data`) |

## Kpis

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/domains/{domain}` | Domain view | Registrar, Principal, Dean, HOD (`view_dashboard`) |
| GET | `/api/facts/{fact_id}` | One source record behind a figure, with its source and status (Lab 9 evidence). | Registrar, Principal, Dean, HOD (`view_dashboard`) |
| GET | `/api/kpis` | List kpis | Registrar, Principal, Dean, HOD (`view_dashboard`) |
| GET | `/api/kpis/{key}` | Drilldown | Registrar, Principal, Dean, HOD (`view_dashboard`) |

## Reports

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/reports/current` | Current | Registrar, Principal, Dean, HOD, Council (`view_reports`) |
| GET | `/api/reports/diff` | Diff | Registrar, Principal, Dean, HOD, Council (`view_reports`) |
| POST | `/api/reports/rollback` | Move the current pointer back. The governance service checks the role and keeps history intact. | Anyone signed in |
| GET | `/api/reports/versions` | Versions | Registrar, Principal, Dean, HOD, Council (`view_reports`) |
| GET | `/api/reports/versions/{number}` | Version detail | Registrar, Principal, Dean, HOD, Council (`view_reports`) |

## Runs

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/plan-catalogue` | Plan catalogue | Registrar, Principal, Dean (`start_run`) |
| GET | `/api/runs` | List runs | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs` | Create run | Registrar, Principal, Dean (`start_run`) |
| GET | `/api/runs/{run_id}` | Get run | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs/{run_id}/answers` | Answer | Registrar, Principal, Dean (`start_run`) |
| GET | `/api/runs/{run_id}/events` | Live progress as server-sent events. A reconnect resumes from Last-Event-ID. | Registrar, Principal, Dean (`start_run`) |
| PUT | `/api/runs/{run_id}/plan` | Edit plan | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs/{run_id}/plan/lock` | Lock plan | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs/{run_id}/plan/revise` | Revise plan | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs/{run_id}/resume` | Resume | Registrar, Principal, Dean (`start_run`) |
| POST | `/api/runs/{run_id}/skip-questions` | Skip questions | Registrar, Principal, Dean (`start_run`) |
| GET | `/api/runs/{run_id}/trace` | Trace | Registrar, Principal (`view_audit`) |

## System

| Method | Path | What it does | Who may call it |
| --- | --- | --- | --- |
| GET | `/api/health` | Health | Public |
| GET | `/api/system/status` | Status | Anyone signed in |
