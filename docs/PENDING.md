# PENDING: what is not ours to finish

Written 2026-10-04. Two lists. The first is what needs the university or someone outside the project, and nothing we do can finish it. The second is what is still ours and not done yet, so it is not hidden among things that are blocked.

## 1. Needs the university, the professor or an outside party

| # | What | From whom | What it blocks | What is already ready on our side |
| --- | --- | --- | --- | --- |
| 1 | Real data extracts for the pilot departments, and the signed Data Requirements Specification | HOD, Registrar or IQAC | The real-data run and reconciliation (build plan day 18) | CSV templates in `data/sample/templates`, CSV and read-only SQL adapters, the validator with plain reasons, `make ingest DIR=...` and its reconciliation report, `make seed` proving the whole path. Mapping a differently named column is a manifest edit. |
| 2 | Approved KPI definitions and targets (NIRF, NAAC, strategic plan) | IQAC | Dropping the `PLACEHOLDER_PENDING_IQAC` marker (rule 12) | KPI formulas are YAML data. Replacing a definition or a target is a data change, with no release. |
| 3 | Four rules only the university can set: placement percentage over eligible or registered students, whether provisional offers count anywhere, how a paper shared by two departments is credited, how stale is stale, and display precision per KPI | IQAC | Official figures. Each has a stated default (DATA_CONTRACT section 5, decisions D12 and D23) | One-line changes in a definition or a setting. |
| 4 | GPU server specification, who decides, and whether the demo may use it | University IT cell | Choosing the production model size. Nothing in the demo needs it | Provider factory, `LLM_LOCAL_HOSTS` allow-list for a university server, and `scripts/evaluate_llm.py` to measure any model you point it at. |
| 5 | Where the system will run after the demo, who hosts it, and a name and TLS if it is reachable | University IT cell | The deployment day and `COOKIE_SECURE` | Everything runs from one machine today. Docker deployment files are listed as still ours below. |
| 6 | Whether each lab must also be submitted as a notebook, or only the live demo is graded | The professor (Kiran to ask, decision C4) | How the labs are packaged | Every lab's work runs from one command, so wrapping it in a notebook is cheap. |
| 7 | The professor's preferred KPIs or brief format | The professor | Tuning the brief to what will be marked | The brief's sections and the KPI list are data. |
| 8 | Faculty feedback on a draft brief (the book's week 3 checkpoint) | Faculty | Nothing is blocked, it improves the result | A complete draft can be produced today. |
| 9 | Real names and roles for the seed users, and SSO if wanted | Registrar and IT cell | Replacing the synthetic personas. SSO is out of scope | Users and roles are managed in the Admin page. |

Outside the university, one thing only the account owner can do:

| What | Who | Why | How |
| --- | --- | --- | --- |
| Let the GitHub login push a workflow file | Kiran | GitHub refuses to add `.github/workflows` unless the token has the `workflow` scope, and granting it needs approval in a browser | `gh auth refresh -h github.com -s workflow`, then `git mv docs/ci/ci.yml .github/workflows/ci.yml`, commit and push. The workflow is written, pinned and linted. |

Not needed any more: a hosted model key. The local model runs through Ollama.

## 2. Still ours, not done

These need no one else. They are split into small parts, with the demo first, in [NEXT_STEPS.md](NEXT_STEPS.md). This table is the same work seen by lab.

| Item | Lab | Why it matters | Rough size |
| --- | --- | --- | --- |
| Acceptance suite as a gate with measured detection and repair rates, and the parallel versus sequential benchmark | 8, 11 | The definition of done asks for measured numbers, not claims. `make acceptance` is a stub that fails loudly. | An hour |
| Framework specialists (NIRF, NAAC, strategic) as a registry of packs over one implementation | 13 | A lab deliverable. Real definitions wait for item 2 above, so these carry the placeholder marker. | An hour |
| MCP connector server with scoped tokens, and agents reading through it | 5 | On the build plan's never-cut list. Today agents read through an in-process interface with the same shape, enforced by a test. | Two to three hours |
| PostgreSQL with pgvector: models, migrations, services, append-only audit role, checkpointer, similar-brief retrieval, data mode read from the database | 4, 6 | Persistence across restarts and rule 7's "checked against the database". Today services are in memory, and real data mode refuses to start for that reason. | The largest item, a few hours |
| Docker compose production profile, backup script, runbook for the IT cell, clean-machine smoke test | 14 | Deployment. | Two hours |
| The hybrid planner (rules first, model second, ask where they disagree) | 1 | The measured weak spot of the small model, see `docs/evals`. | An hour, optional |
