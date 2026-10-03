# Language model evaluation: fake:canned

Run on 2026-10-03, synthetic data only, seed 7, temperature 0.2, 1 draft trials per KPI. Total time 0 s.

Labels are my reading of the requests, not ground truth from the university. The rule-based canned model is the baseline: run this script with `--provider fake` to see it.

## Planner: ten requests

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

Each draft is composed into a brief and put through checks V1 to V9. 3 drafts.

- Produced a draft at all: **3/3 (100%)**
- Needed no repair inside the call (first try): **3/3 (100%)**
- Passed the validation gate: **3/3 (100%)**
- Time per draft: median 0.0 s, slowest 0.0 s

| KPI | Seed | Calls | Seconds | Result |
| --- | --- | --- | --- | --- |
| AC_PASS_PCT | 7 | 1 | 0.0 | passes |
| RS_PUB_PF | 7 | 1 | 0.0 | passes |
| PL_PCT | 7 | 1 | 0.0 | passes |
