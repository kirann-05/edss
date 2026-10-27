# 10. Testing and results

All results below are from one run of every suite on 27 Oct 2026, on `main`, on the development MacBook Air (Apple Silicon, 10 cores). Raw logs: `results/2026-10-27/`. Summary and machine-readable figures: `results/2026-10-27/summary.md`, `results/2026-10-27/metrics.json`.

## 10.1 Strategy

| Level | What is tested | Tool |
| --- | --- | --- |
| Unit | KPI engine and formulas, each validation check, tokens, planner, repair, audit chain, ingestion validator, flags and formatting | pytest, Vitest |
| Component | Web components (decision dialogs, run timeline, rich text with figure tokens, error panel) | Vitest, Testing Library |
| Integration (API) | Every route with every role: permissions, scoping, approvals, rollback, audit filters | pytest with FastAPI's test client |
| Integration (database) | The same API suite with everything stored in PostgreSQL; migrations; audit role and trigger; backup and restore; real-data loading | pytest against a scratch PostgreSQL |
| Connector | Identical KPIs through MCP and directly; out-of-scope reads refused and audited | pytest |
| End to end (browser) | The approval flow, fault injection, scoping, keyboard use, accessibility (axe), protective headers | Playwright |
| Demo rehearsal | A browser walks the nine demo steps exactly as `docs/DEMO.md` says, at projector size | Playwright |
| Fault injection | Every fault into every plan it applies to | `scripts/acceptance.py` |
| Performance | Parallel against one-at-a-time domain agents | `scripts/benchmark.py` |
| Deployment | A fresh clone built into containers, used, backed up and restored | `scripts/smoke_clean_clone.sh` |
| Model quality | Option drafting and planning with a real local model | `scripts/evaluate_llm.py` |

Tests were written first for the KPI engine and every validation check. Key tests were also proved by breaking the code on purpose and watching exactly that test fail (validation branches, the date shown on an as-of figure).

## 10.2 Today's run

| Suite | Command | Result | Time |
| --- | --- | --- | --- |
| Lint, types, backend and web unit tests | `make check` | 1,136 backend passed (2 skipped by design: one runs only in database mode, one needs a running local model); 238 web tests in 17 files passed | 58 s |
| Database layer | `make test-db` | 68 passed, 1 skipped (needs a running local model) | 14 s |
| API suite in database mode | `make test-api-db` | 242 passed | 22 s |
| Browser tests | `make e2e` | 18 passed | 46 s |
| Demo rehearsal | `make rehearse` | 9 of 9 steps (and the check that DEMO.md and the test agree) | 18 s |
| Fault injection | `make acceptance` | 94 of 94 caught and repaired | 2 s |
| Benchmark | `make benchmark` | 4.0 times faster in parallel | 30 s |
| Coverage | `make coverage` | 98 percent of backend lines (6,655 statements, 104 not run) | 91 s |
| Fresh clone in containers | `make smoke` | Passed: built and healthy in 101 s, a brief reached review, the audit chain verified over 40 rows, the backup restored | 103 s |

In all: **1,392 automated tests** (1,136 backend, 238 web, 18 browser), all passing.

## 10.3 Browser tests (18)

The sign-in page; every page the Registrar can open and its main states; the Administrator's people page and its dialogs; the Governing Council reads published reports; the Principal asks for a brief, approves it and rolls the report back; a figure typed into an edit is refused and nothing is published; an injected fault is caught, repaired and shown to the reviewer; pages and the API cannot be framed and do not name the server (2); the skip link; a KPI's drill-down from the keyboard; approving with the keyboard alone with focus trapped in the dialog; Escape closes a dialog without deciding; the Registrar refreshes the data; people who may not refresh are refused by the server; a HOD sees only their own department's detail; wrong passwords lock an email after five; signing out ends the session. An axe accessibility scan (WCAG 2.2 AA rules) runs over every page in the Registrar walk.

## 10.4 Fault injection (`make acceptance`)

18 plans (every period, each with all four areas, each area alone, and placement with research); 113 graph runs in 1.2 seconds.

| Measure | Result |
| --- | --- |
| Clean drafts passing all nine checks first time | 18 of 18 |
| Fault trials | 94 |
| Caught on the first attempt | 94 of 94 |
| Caught by the check meant to catch it | 94 of 94 |
| Also failed an unrelated check | 0 of 94 |
| Repaired inside the budget of 3 | 94 of 94 |
| Escalated to a person | 0 |

| Fault | Caught by |
| --- | --- |
| A figure written by hand | V1 |
| A figure with no source | V7 |
| A provisional figure called confirmed | V4 |
| An option with no risks | V3 |
| A stale department hidden | V2, V8 |
| A shared paper counted twice | V9 |
| A miss rounded into a pass | V6 |
| Approval claimed without a record | V5 |

Full table: `results/2026-10-27/acceptance-report.md`.

## 10.5 Benchmark (`make benchmark`)

Each domain agent waits a simulated delay before reading, standing in for a slow university system. Median of 3 runs.

| Delay per agent | Domain phase, parallel | One at a time | Speed-up |
| --- | --- | --- | --- |
| 0 ms | 1 ms | 1 ms | nothing to win |
| 250 ms | 258 ms | 1,025 ms | 4.0 times |
| 700 ms | 709 ms | 2,821 ms | 4.0 times |
| 1,000 ms | 1,007 ms | 4,021 ms | 4.0 times |

Four agents waiting the same time can be at most four times faster, so this is the best possible result. Full report: `results/2026-10-27/benchmark.md`.

## 10.6 Coverage (`make coverage`)

98 percent of backend lines run under a test, across every suite including database mode. The few lines not run are mostly calls to a running local model and the keep-alive of a long event stream. Reading what coverage missed found five real bugs, all fixed with tests (listed in `docs/VIVA_NOTES.md`). Full report: `results/2026-10-27/coverage.txt`.

## 10.7 Model evaluation (`docs/evals`)

qwen3.5 with 4 billion parameters through Ollama on the MacBook Air, synthetic data only.

| Measured | Result |
| --- | --- |
| Option drafts passing all nine checks | 9 of 9 |
| Option drafts needing a repair | 0 of 9 (1 of 9 with framework guidance, repaired in the same call) |
| Time per option draft | median 27.9 s |
| Planner, model alone: right questions / plans fully right | 4 of 10 / 4 of 6 |
| Planner as built, rules first and the model second | 9 of 10 / 6 of 6, with 6 model calls instead of 16 |
| A full brief end to end with the real model | about a minute (one area: 27 s) |

## 10.8 Known gaps in testing, said plainly

- Web pages are proved by browser tests, not unit tests, so a rarely used page state could still hide a bug.
- Model quality is measured on synthetic data with a 4B model on a laptop; the university's GPU model must be measured again with `scripts/evaluate_llm.py`.
- Real university data has not been loaded yet; the real-data path is tested with exported synthetic files and a CO and PO-only folder.
