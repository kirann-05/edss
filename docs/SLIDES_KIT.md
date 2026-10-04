# Slides kit

Everything the slides need, in one place. Every number below has its source next to it. If a slide needs a number that is not here, ask Kiran rather than estimating it.

Checked on 2026-10-04 against commit `e42ce00` and the files named.

## The four diagrams

PNG for any slide tool, SVG to scale without blur (PowerPoint and Keynote take SVG, Google Slides does not). 16:9, white background.

| File | Use it for |
| --- | --- |
| `docs/diagrams/1-system.png` | How the parts fit. Dashed boxes are planned, not built |
| `docs/diagrams/2-agent-graph.png` | One run, step by step, and which steps use the language model |
| `docs/diagrams/3-numbers-by-reference.png` | Why the model cannot get a number wrong |
| `docs/diagrams/4-governance.png` | Approval, versions, rollback and the audit chain |

To change one: edit the SVG, then `make diagrams`.

Screenshots of the nine demo steps, at projector size, are in `docs/demo-screens/step-1.png` to `step-9.png`.

## What the system does, in one sentence

Four domain agents gather department data in parallel through one governed connector, plain code turns it into institution KPIs against targets, a language model drafts options and risks for every KPI off target, nine checks gate the draft and repair what fails, and only then does a named person approve, edit or override it.

## Measured facts

| Fact | Number | Source |
| --- | --- | --- |
| Backend tests | 991, all passing | `make check` |
| Frontend unit and component tests | 224 in 14 files, all passing | `make check` |
| Browser tests, real API and pages | 15, all passing, including an accessibility scan (WCAG 2.2 AA rules) | `make e2e` |
| The whole demo walked by a browser | 9 steps in about 9 seconds | `make rehearse` |
| Synthetic data | 8 departments, 3 academic years (2023-24 to 2025-26), fixed seed, so every run gives the same figures | `docs/DATA_CONTRACT.md` section 6 |
| Traps planted in that data | 10, each with its own test (15 trap tests in all) | `backend/tests/synthetic/test_traps.py`, `test_trap_checks.py` |
| Validation checks on every draft | 9 (V1 to V9) | `backend/app/agents/validation/checks.py` |
| Faults that can be injected live | 8, each caught and repaired inside the retry budget | `backend/tests/agents/test_graph.py`, `test_every_fault_is_detected_and_repaired_inside_the_budget` |
| Acceptance run | 18 plans; 94 fault trials, 94 caught first time by the intended check, 94 repaired; 18 of 18 clean drafts pass first time | `make acceptance`, `docs/acceptance-report.md` |
| Retry budget | 3 attempts, then the draft goes to a person with a diagnosis | `max_attempts` in `backend/app/core/config.py` |
| Parallel domain agents | 4, each waiting 700 ms to stand in for a slow source; a whole run in the demo takes about one second, reads through MCP included | Shown on the run page, `docs/demo-screens/step-3.png` |
| Parallel against one at a time | With a simulated 700 ms source per agent, the domain phase takes about 0.71 s in parallel and 2.8 s one at a time, close to the best possible four times. With no delay there is nothing to win | `make benchmark`, `docs/benchmark.md` |
| Connector over MCP | Every read the agents make goes through an MCP server with a token for the run's areas only. A whole run gives identical KPIs and brief through MCP and directly; a read outside the token's areas is refused and audited | `backend/tests/mcp_connector` (27 tests) |
| Framework specialists (Lab 13) | 3 packs over one implementation: Strategic plan active and guiding every draft; NIRF and NAAC registered but empty until IQAC supplies definitions, and every brief says so | `backend/tests/specialists` (13 tests) |
| Audit chain | SHA-256, each row hashing the previous hash with its own content | `backend/app/governance/audit.py` |
| Tampering found | A changed row is found at exactly that row | `backend/tests/api/test_audit_api.py`, `test_tampering_is_detected_at_the_row_that_was_changed` |
| Sign-in throttle | After 5 failed sign-ins in 15 minutes, that email is refused for a while | `backend/tests/test_throttle.py` |

## The ten traps (and what the system does with each)

These are planted in the synthetic data on purpose, to prove the system does not hide problems.

| Trap | Planted | What the system does |
| --- | --- | --- |
| T1 | One department's placement data is five months old | Flags it stale, everywhere it is used |
| T2 | One department has no research record this year | Leaves it out and says so, never counts it as zero |
| T3 | About 12 percent of offers are provisional | Keeps them out of the placement figure, shown apart with a badge |
| T4 | The open finance quarter has forecast revenue | Never adds it to actuals |
| T5 | Two departments share one paper | Counts it once for the institution, credits both departments |
| T6 | Placement computes to 74.96 against a target of 75 | Shows 75.0 but marks it missed |
| T7 | Department pass rates average higher than the true institution rate | Builds the institution figure from totals |
| T8 | One finance figure is still being reconciled | Badges it, keeps it out of actuals, lists it in the assumptions |
| T9 | One department has nothing to divide by | No value for that department, not zero and not 100 |
| T10 | Two KPIs miss, one is at risk, the rest are met | Gives the brief something to decide |

## The language model, measured

A small local model (qwen3.5, 4 billion parameters, through Ollama) on Kiran's MacBook Air, synthetic data only. Full report: `docs/evals/ollama-qwen3.5-4b-v2-current-prompts-2026-10-03.md`.

| What was measured | Result |
| --- | --- |
| Option drafts that passed all nine checks | 9 of 9 |
| Option drafts that needed a repair | 0 of 9 |
| Time per option draft | median 27.9 seconds |
| Option drafts that needed a repair, with the framework guidance | 1 of 9, repaired inside the same call |
| Planner, the model alone: right questions / plans fully right | 4 of 10 / 4 of 6 |
| Planner as the app runs it, rules first and the model second | 9 of 10 / 6 of 6, with 6 model calls instead of 16 |

What to say: drafting is reliable. Reading a request is where a small model is weak, so the rules read it first and the model only flags what they may have missed; a person reviews every plan. The demo uses canned drafts so it is fast and the same every time; production runs the model on the university GPU.

## Say plainly on any slide that shows figures

- All data is synthetic. Real data is waiting on the university (`docs/PENDING.md`).
- All 13 KPI definitions and targets are placeholders until the university's IQAC supplies the official ones. The dashboard and every brief say so.
- Nothing is published without a named approver. Every figure opens to its source record.

## Not built yet

Do not show these as working. The system diagram draws them dashed.

- The demo itself runs in memory. PostgreSQL storage is built and tested (`EDSS_DATABASE=true`, `make test-api-db`), but the demo does not use it
- Docker packaging
