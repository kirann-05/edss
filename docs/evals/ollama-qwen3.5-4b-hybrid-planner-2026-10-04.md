# Language model evaluation: ollama:qwen3.5:4b

Run on 2026-10-04, synthetic data only, seed 7, temperature 0.2, 3 draft trials per KPI. Total time 31 s.

Labels are my reading of the requests, not ground truth from the university. The rule-based canned model is the baseline: run this script with `--provider fake` to see it.

## Planner: ten requests

Planner: rules first, the model second (decision D30), as the app runs. Model calls made by the planner: 6.

- Asked exactly the right questions: **9/10 (90%)**
- Plan fully right (period, areas, audience, options scope): **6/6 (100%)**
  - period: 6/6 (100%)
  - areas: 6/6 (100%)
  - audience: 6/6 (100%)
  - options_for: 6/6 (100%)
- Could not answer at all: **0**

| Request | Asked (expected) | Asked (got) | Plan |
| --- | --- | --- | --- |
| Prepare the leadership brief | audience, period, scope | audience, period, scope | n/a |
| How are we doing? | audience, period, scope | audience, period, scope | n/a |
| Where did we miss target this year, and what should we do about it? | audience, scope | audience, scope | n/a |
| Prepare the placement brief | audience, period | audience, period | n/a |
| Placement and research brief for the Governing Council for 2025-26 | nothing |  | right |
| Finance brief for the Registrar for last year | nothing |  | right |
| Brief for the board on everything, with options for every KPI, for 2024-25 | nothing |  | right |
| Academic results for the Principal this year | nothing |  | right |
| Research output and grants brief for the council for 2023-24 | nothing |  | right |
| Institution-wide overview for leadership for 2025-26, only the KPIs that are off target | nothing | audience | right |

## Drafter: option text for every off-target KPI

Each draft is composed into a brief and put through checks V1 to V9. 0 drafts.

- Produced a draft at all: **n/a**
- Needed no repair inside the call (first try): **n/a**
- Passed the validation gate: **n/a**
- Tokens: 10578 in, 536 out over 6 calls (18 tokens per second)
- Empty answers (thinking used the budget): 0. Not JSON: 0

| KPI | Seed | Calls | Seconds | Result |
| --- | --- | --- | --- | --- |
