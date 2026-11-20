# Assignment 3: Skill Creation: reusable plan and options skills

Lab 3 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 3 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Reusable skills with a contract

## What was built, and where

[`app/agents/skills/plan_skill.py`](../../Course-Project/backend/app/agents/skills/plan_skill.py), `options_skill.py`: each a schema, a code-side check, and its prompt as data in [`app/agents/prompts.py`](../../Course-Project/backend/app/agents/prompts.py)

## How to show it

Open `prompts.py` and one skill: what the model is told, what comes back, what is checked

## How it is proved

[`tests/agents/test_plan_skill.py`](../../Course-Project/backend/tests/agents/test_plan_skill.py), `test_options_skill.py`, `test_prompts.py`, `test_real_model_skills.py`

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_plan_skill.py
```

Result when this README was written: **39 passed in 0.03s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
