# Language model evaluation: ollama:qwen3.5:4b

Run on 2026-10-03, synthetic data only, seed 7, temperature 0.2, 3 draft trials per KPI. Total time 326 s.

Labels are my reading of the requests, not ground truth from the university. The rule-based canned model is the baseline: run this script with `--provider fake` to see it.

## Planner: ten requests

- Asked exactly the right questions: **4/10 (40%)**
- Plan fully right (period, areas, audience, options scope): **4/6 (67%)**
  - period: 6/6 (100%)
  - areas: 5/6 (83%)
  - audience: 6/6 (100%)
  - options_for: 4/6 (67%)
- Could not answer at all: **0**

| Request | Asked (expected) | Asked (got) | Plan |
| --- | --- | --- | --- |
| Prepare the leadership brief | audience, period, scope | audience, period | n/a |
| How are we doing? | audience, period, scope | audience, period | n/a |
| Where did we miss target this year, and what should we do about it? | audience, scope | audience, period | n/a |
| Prepare the placement brief | audience, period | audience, period, scope | n/a |
| Placement and research brief for the Governing Council for 2025-26 | nothing |  | wrong: areas, options_for |
| Finance brief for the Registrar for last year | nothing | audience, period | right |
| Brief for the board on everything, with options for every KPI, for 2024-25 | nothing |  | right |
| Academic results for the Principal this year | nothing | audience, period | right |
| Research output and grants brief for the council for 2023-24 | nothing |  | wrong: options_for |
| Institution-wide overview for leadership for 2025-26, only the KPIs that are off target | nothing |  | right |

## Drafter: option text for every off-target KPI

Each draft is composed into a brief and put through checks V1 to V9. 9 drafts.

- Produced a draft at all: **9/9 (100%)**
- Needed no repair inside the call (first try): **9/9 (100%)**
- Passed the validation gate: **9/9 (100%)**
- Time per draft: median 27.9 s, slowest 33.8 s
- Tokens: 27831 in, 1231 out over 16 calls (17 tokens per second)
- Empty answers (thinking used the budget): 0. Not JSON: 0

| KPI | Seed | Calls | Seconds | Result |
| --- | --- | --- | --- | --- |
| AC_PASS_PCT | 7 | 1 | 24.5 | passes |
| AC_PASS_PCT | 8 | 1 | 29.6 | passes |
| AC_PASS_PCT | 9 | 1 | 33.8 | passes |
| RS_PUB_PF | 7 | 1 | 31.0 | passes |
| RS_PUB_PF | 8 | 1 | 24.9 | passes |
| RS_PUB_PF | 9 | 1 | 24.3 | passes |
| PL_PCT | 7 | 1 | 31.5 | passes |
| PL_PCT | 8 | 1 | 27.9 | passes |
| PL_PCT | 9 | 1 | 26.8 | passes |
