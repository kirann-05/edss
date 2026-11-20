# Language model evaluation: ollama:qwen3.5:4b

Run on 2026-10-03, synthetic data only, seed 7, temperature 0.2, 3 draft trials per KPI. Total time 537 s.

Labels are my reading of the requests, not ground truth from the university. The rule-based canned model is the baseline: run this script with `--provider fake` to see it.

## Planner: ten requests

- Asked exactly the right questions: **2/10 (20%)**
- Plan fully right (period, areas, audience, options scope): **2/6 (33%)**
  - period: 6/6 (100%)
  - areas: 2/6 (33%)
  - audience: 6/6 (100%)
  - options_for: 3/6 (50%)
- Could not answer at all: **0**

| Request | Asked (expected) | Asked (got) | Plan |
| --- | --- | --- | --- |
| Prepare the leadership brief | audience, period, scope | audience, period, scope | n/a |
| How are we doing? | audience, period, scope | audience, period, scope | n/a |
| Where did we miss target this year, and what should we do about it? | audience, scope | audience, period, scope | n/a |
| Prepare the placement brief | audience, period | audience, period, scope | n/a |
| Placement and research brief for the Governing Council for 2025-26 | nothing | scope | wrong: areas, options_for |
| Finance brief for the Registrar for last year | nothing | audience, period, scope | wrong: areas |
| Brief for the board on everything, with options for every KPI, for 2024-25 | nothing | audience, period, scope | right |
| Academic results for the Principal this year | nothing | audience, period, scope | wrong: areas, options_for |
| Research output and grants brief for the council for 2023-24 | nothing | audience, scope | wrong: areas, options_for |
| Institution-wide overview for leadership for 2025-26, only the KPIs that are off target | nothing | audience, scope | right |

## Drafter: option text for every off-target KPI

Each draft is composed into a brief and put through checks V1 to V9. 9 drafts.

- Produced a draft at all: **7/9 (78%)**
- Needed no repair inside the call (first try): **5/9 (56%)**
- Passed the validation gate: **7/9 (78%)**
- Time per draft: median 32.0 s, slowest 90.8 s
- Tokens: 15552 in, 2679 out over 16 calls (22 tokens per second)
- Empty answers (thinking used the budget): 0. Not JSON: 0

| KPI | Seed | Calls | Seconds | Result |
| --- | --- | --- | --- | --- |
| AC_PASS_PCT | 7 | 2 | 50.3 | passes |
| AC_PASS_PCT | 8 | 1 | 28.0 | passes |
| AC_PASS_PCT | 9 | 2 | 45.8 | passes |
| RS_PUB_PF | 7 | 1 | 24.5 | passes |
| RS_PUB_PF | 8 | 3 | 90.8 | LLMOutputError: draft_options: output did not fit after 2 repairs: option 1 contains figures written by hand (one). Write figures only as reference tokens, and avoid spelled-out numbers too |
| RS_PUB_PF | 9 | 1 | 27.8 | passes |
| PL_PCT | 7 | 1 | 24.4 | passes |
| PL_PCT | 8 | 3 | 89.2 | LLMOutputError: draft_options: output did not fit after 2 repairs: option 3 contains figures written by hand (one). Write figures only as reference tokens, and avoid spelled-out numbers too |
| PL_PCT | 9 | 1 | 32.0 | passes |
