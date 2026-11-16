# Assignment 1: Agent vs Chatbot (the decision-brief planner loop)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Establish the agent loop (clarify, plan, revise) instead of a one-shot chatbot answer. A minimal planner clarifies the request, proposes a plan for producing the decision brief with options and risks, and revises it on feedback. The book's pitfall: without clarify and revise it is a chatbot, not an agent.

## Concept applied in EDSS

In EDSS the "request" is a leadership ask such as "prepare the brief for the next review". On its own that request is missing the two things every brief needs: which review cycle and which domains (academic, research, placement, finance). The Coordinator asks for the missing pieces, turns the answers into a structured plan (KPIs, constraints, requester), and then accepts leadership feedback that narrows the scope. The output is a plan, not a final answer.

## Technical stack

- Python 3, standard library only (`dataclasses`, `uuid`, `json`)
- `eds` package from [`../lab_kit/eds/`](../lab_kit/eds/)
- Notebook version: Google Colab / Jupyter, optional Gemini (`gemini-2.5-flash`) with a rule-based `OfflineBrain` fallback

## Implementation

Script: [`lab01_planner_loop.py`](lab01_planner_loop.py)

1. Starts from a deliberately vague request: an empty dict `{}`.
2. Calls `Coordinator.clarify()` ([`coordinator.py`](../lab_kit/eds/coordinator.py)). It checks which of `review_cycle` and `domains` are missing and asks one question for each. A small `scripted_user_answers()` function stands in for the human, answering "Q1 FY26 Governing Council review" and "academic,research,placement,finance".
3. Asserts that at least two clarifying questions were asked.
4. Normalises the domains answer into a list and calls `Coordinator.build_plan()`, which delegates to `plan_skill()` in [`skills.py`](../lab_kit/eds/skills.py). This fills defaults (the six institution KPIs and four governance constraints) and returns a frozen `Plan` dataclass.
5. Calls `Coordinator.revise_plan(plan, {"domains": ["academic", "finance"]})`, simulating leadership narrowing the scope. Revision merges the feedback into the old plan and produces a new locked `Plan`.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `Coordinator.clarify` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Asks for each missing input; records the questions asked |
| `Coordinator.build_plan` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Proposes the plan via `plan_skill` |
| `Coordinator.revise_plan` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Applies feedback and re-locks the plan |
| `Plan`, `plan_skill` | [`skills.py`](../lab_kit/eds/skills.py) | Immutable plan object with defaults |

## Notebook (Assignment 1 and 2 tasks)

[`notebook/LAB_1_Worklet15_Executive_Decision_Support.ipynb`](notebook/LAB_1_Worklet15_Executive_Decision_Support.ipynb) is the fuller Colab version of this lab. It runs with or without a `GEMINI_API_KEY`; without one, a rule-based `OfflineBrain` returns the same JSON structures, so every cell executes. The committed outputs are from an offline run.

- Assignment 1 (Cell 10): two independent feedback rounds that mutate the same plan object, shown by `id(plan)` and a field-level diff.
- Assignment 2 (Cells 9 and 11): conflict detection, with provisional Finance figures in Run A and an unsourceable KPI in Run B.
- Cell 13 runs the rubric as assertions; Cell 14 writes the artifacts in [`notebook/lab1_artifacts/`](notebook/lab1_artifacts/) (iteration log, prompt log, final plan, Run B plan, acceptance checks).

## How to run

```bash
cd Assignments/Assignment-01_Agent_vs_Chatbot
python lab01_planner_loop.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): given a vague request, the agent asks at least two clarifying questions and yields a coherent, editable plan.

From [`output/run_log.txt`](output/run_log.txt):

```
Incoming request: {}

Clarifying questions asked (2):
  - Which review cycle is this for (e.g. Q1 FY26, NAAC snapshot)?
  - Which domains should be included (academic / research / placement / finance, or all)?
...
Revised plan (leadership narrowed scope to academic + finance):
  review_cycle: Q1 FY26 Governing Council review
  domains: ['academic', 'finance']
...
ACCEPT: >=2 clarifying questions asked, and a coherent, editable plan was produced.
```

Notebook evidence: [`lab1_acceptance_checks.json`](notebook/lab1_artifacts/lab1_acceptance_checks.json) records 16 of 16 acceptance checks passed (for example "vague request triggers >= 2 clarifying questions" with 6 questions asked in round 1, and "two revision rounds applied").

Note: the script's revision produces a new frozen `Plan` rather than editing the old one in place; the notebook is where the same-object revision is demonstrated.

## In the full system

| | |
| --- | --- |
| Production code | [`app/agents/skills/plan_skill.py`](../../Course_Project/backend/app/agents/skills/plan_skill.py), [`app/services/runs.py`](../../Course_Project/backend/app/services/runs.py) |
| What it does there | A new brief asks its questions, shows the plan, lets the user untick a KPI and save ("Revision 2"), then locks the plan |
| Proved by | [`tests/agents/test_plan_skill.py`](../../Course_Project/backend/tests/agents/test_plan_skill.py), [`tests/agents/test_hybrid_planner.py`](../../Course_Project/backend/tests/agents/test_hybrid_planner.py), [`tests/api/test_runs_api.py`](../../Course_Project/backend/tests/api/test_runs_api.py) |
