# Assignment 9: Deep Research: grounding and evidence

Lab 9 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 9 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Grounding and evidence

## What was built, and where

Reference tokens `{{kpi:...}}` and `{{fact:...}}` in [`app/agents/tokens.py`](../../Course-Project/backend/app/agents/tokens.py); check V1

## How to show it

A brief: click any figure, then a source record with its system, reference and as-of date (docs/DEMO.md steps 4 and 5)

## How it is proved

[`tests/agents/test_tokens.py`](../../Course-Project/backend/tests/agents/test_tokens.py), `test_validation.py`

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_tokens.py
```

Result when this README was written: **38 passed in 0.02s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
