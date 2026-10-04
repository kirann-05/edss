# Language model evaluation: ollama:qwen3.5:4b

Run on 2026-10-04, synthetic data only, seed 7, temperature 0.2, 3 draft trials per KPI. Total time 201 s.

Labels are my reading of the requests, not ground truth from the university. The rule-based canned model is the baseline: run this script with `--provider fake` to see it.

## Planner: ten requests

Planner: rules first, the model second (decision D30), as the app runs. Model calls made by the planner: 0.

- Asked exactly the right questions: **n/a**
- Plan fully right (period, areas, audience, options scope): **n/a**
  - period: n/a
  - areas: n/a
  - audience: n/a
  - options_for: n/a
- Could not answer at all: **0**

| Request | Asked (expected) | Asked (got) | Plan |
| --- | --- | --- | --- |

## Drafter: option text for every off-target KPI

Each draft is composed into a brief and put through checks V1 to V9. 9 drafts.

- Produced a draft at all: **9/9 (100%)**
- Needed no repair inside the call (first try): **8/9 (89%)**
- Passed the validation gate: **9/9 (100%)**
- Time per draft: median 17.6 s, slowest 40.8 s
- Tokens: 9406 in, 6114 out over 10 calls (30 tokens per second)
- Empty answers (thinking used the budget): 0. Not JSON: 0

| KPI | Seed | Calls | Seconds | Result |
| --- | --- | --- | --- | --- |
| AC_PASS_PCT | 7 | 1 | 17.0 | passes |
| AC_PASS_PCT | 8 | 1 | 16.3 | passes |
| AC_PASS_PCT | 9 | 1 | 16.4 | passes |
| RS_PUB_PF | 7 | 1 | 17.6 | passes |
| RS_PUB_PF | 8 | 1 | 14.0 | passes |
| RS_PUB_PF | 9 | 2 | 40.8 | passes |
| PL_PCT | 7 | 1 | 26.6 | passes |
| PL_PCT | 8 | 1 | 27.3 | passes |
| PL_PCT | 9 | 1 | 24.4 | passes |
