# Language model evaluations

Measured by `scripts/evaluate_llm.py` on synthetic data, one run each, seed 7, temperature 0.2.

| Report | What it is |
| --- | --- |
| `fake-canned-*` | The rule-based canned model, as a baseline. I wrote it against the same vocabulary the test requests use, so it is not an independent yardstick. |
| `ollama-qwen3.5-4b-v1-first-prompts-*` | `qwen3.5:4b` on a MacBook Air through Ollama, with the first prompts. |
| `ollama-qwen3.5-4b-v2-current-prompts-*` | The same model with the current prompts: worked examples built from the real periods, wording that rules out number words, and a different random seed on each repair. |

## What the numbers say

| | v1 | v2 | canned baseline |
| --- | --- | --- | --- |
| Drafts that pass the full validation gate (9 drafts) | 7 of 9 | **9 of 9** | 3 of 3 |
| Drafts needing no repair at all | 5 of 9 | **9 of 9** | 3 of 3 |
| Planner asks exactly the right questions (10 requests) | 2 of 10 | 4 of 10 | 9 of 10 |
| Plan fully right (6 specific requests) | 2 of 6 | 4 of 6 | 6 of 6 |
| Median time per draft | 32 s | 28 s | instant |

- **Drafting is the job a small local model can be trusted with here**, because it is boxed in on both sides: it is never given a figure, it can only refer to one by token, and every draft goes through the same nine checks as the canned one.
- **Interpreting a request is where it is weakest.** It asks for things the request already says, and sometimes plans more areas than were asked for. The rule-based baseline is better at this, so a reasonable design is rules first and the model second, or both with a question asked where they disagree. That hybrid is not built.
- A person reviews the plan before anything runs, and the drafts before anything is published, so these misses cost a click and not a wrong report.

## Limits to say out loud

- Labels are my reading of the requests, not ground truth from the university.
- One run per version. Three drafts per KPI is enough to see a pattern, not to quote a rate to a decimal place.
- In the two real-model reports the token and speed line counts only the planner's calls. The script was fixed afterwards to total every call, and a re-run produces the corrected line.
- Re-run with `cd backend && uv run python ../scripts/evaluate_llm.py --provider ollama --model qwen3.5:4b --trials 3` (about six minutes).
