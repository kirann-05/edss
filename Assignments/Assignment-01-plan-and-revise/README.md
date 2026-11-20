# Assignment 1: Agent vs Chatbot: plan and revise

Lab 1 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 1 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Plan and revise: a vague request is clarified, planned, revised, locked

## What was built, and where

[`app/agents/skills/plan_skill.py`](../../Course-Project/backend/app/agents/skills/plan_skill.py), [`app/services/runs.py`](../../Course-Project/backend/app/services/runs.py)

## How to show it

New brief, "Prepare the leadership brief": the three questions, the plan, untick a KPI, save, "Revision 2", lock (docs/DEMO.md step 2)

## How it is proved

[`tests/agents/test_plan_skill.py`](../../Course-Project/backend/tests/agents/test_plan_skill.py), `test_hybrid_planner.py`, [`tests/api/test_runs_api.py`](../../Course-Project/backend/tests/api/test_runs_api.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_plan_skill.py tests/api/test_runs_api.py
```

Result when this README was written: **73 passed in 7.89s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
